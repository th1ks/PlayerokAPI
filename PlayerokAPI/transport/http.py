"""Общий HTTP-слой: один `httpx.AsyncClient` на все транспорты."""

from __future__ import annotations

import asyncio
import json as jsonlib
import logging
from typing import Any

import httpx

from ..common.endpoints import (
    COOKIE_DOMAIN,
    DEFAULT_USER_AGENT,
    TOKEN_COOKIE,
    WEB_ORIGIN,
)
from ..common.utils import RateLimiter, backoff_delays
from ..exceptions import (
    NetworkError,
    RequestTimeoutError,
    error_for_status,
)

__all__ = ["HttpTransport"]

logger = logging.getLogger("PlayerokAPI.http")

#: Методы, которые безопасно повторить после 5xx.
_IDEMPOTENT = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class HttpTransport:
    """Тонкая обёртка над httpx: токен, ретраи, лимит частоты.

    Токен живёт в cookie-джаре на домене `.playerok.com`, поэтому уходит
    во все поддомены разом. Для BFF он дополнительно кладётся в заголовок
    `Authorization` — этим занимается REST-транспорт.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 20.0,
        retries: int = 3,
        rate_limit: tuple[int, float] | None = None,
        proxy: str | None = None,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._retries = max(0, retries)
        self._limiter = RateLimiter(*rate_limit) if rate_limit else None
        self._owns_client = client is None

        base_headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Origin": WEB_ORIGIN,
            "Referer": f"{WEB_ORIGIN}/",
        }
        if headers:
            base_headers.update(headers)

        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers=base_headers,
            proxy=proxy,
        )
        self._token: str | None = None
        self.token = token

    # --- токен -----------------------------------------------------------

    @property
    def token(self) -> str | None:
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value or None
        jar = self._client.cookies.jar
        for cookie in list(jar):
            domain = cookie.domain.lstrip(".")
            if cookie.name == TOKEN_COOKIE and (
                domain == "playerok.com" or domain.endswith(".playerok.com")
            ):
                jar.clear(cookie.domain, cookie.path, cookie.name)
        if self._token:
            self._client.cookies.set(TOKEN_COOKIE, self._token, domain=COOKIE_DOMAIN)

    @property
    def client(self) -> httpx.AsyncClient:
        """Живой httpx-клиент — на случай, если нужен нестандартный запрос."""
        return self._client

    # --- запросы ---------------------------------------------------------

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
        parse_json: bool = True,
    ) -> Any:
        """Выполнить запрос и вернуть разобранное тело.

        Ошибочный статус превращается в исключение из `exceptions`.
        При `parse_json=False` возвращаются сырые байты.
        """
        response = await self.raw_request(
            method,
            url,
            params=params,
            json=json,
            data=data,
            files=files,
            content=content,
            headers=headers,
        )
        if not parse_json:
            return response.content
        return _decode(response)

    async def raw_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """То же самое, но отдаёт сам ответ. Статус всё равно проверяется."""
        method = method.upper()
        last_error: Exception | None = None
        delays = [*backoff_delays(self._retries)]

        for attempt in range(self._retries + 1):
            if self._limiter:
                await self._limiter.acquire()
            try:
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                    content=content,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_error = RequestTimeoutError(f"Таймаут запроса {method} {url}")
                last_error.__cause__ = exc
            except httpx.TransportError as exc:
                last_error = NetworkError(f"Сетевая ошибка на {method} {url}: {exc}")
                last_error.__cause__ = exc
            else:
                if response.status_code < 400:
                    return response
                retry_after = _retry_after(response)
                if not _should_retry(method, response.status_code) or attempt >= self._retries:
                    raise error_for_status(
                        response.status_code,
                        str(response.request.url),
                        _decode_safe(response),
                        retry_after,
                    )
                logger.debug(
                    "Повтор %s %s после %s (попытка %s)",
                    method,
                    url,
                    response.status_code,
                    attempt + 1,
                )
                await asyncio.sleep(retry_after if retry_after is not None else delays[attempt])
                continue

            if attempt >= self._retries or method not in _IDEMPOTENT:
                raise last_error
            logger.debug("Повтор %s %s после %s", method, url, last_error)
            await asyncio.sleep(delays[attempt])

        raise last_error or NetworkError(f"Запрос {method} {url} не удался")

    # --- жизненный цикл --------------------------------------------------

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> HttpTransport:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


def _should_retry(method: str, status_code: int) -> bool:
    if status_code == 429:
        return True
    return status_code >= 500 and method in _IDEMPOTENT


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _decode(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except (ValueError, jsonlib.JSONDecodeError):
        return response.text


def _decode_safe(response: httpx.Response) -> Any:
    try:
        return _decode(response)
    except Exception:
        return None
