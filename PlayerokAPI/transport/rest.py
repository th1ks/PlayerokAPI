"""REST-транспорт поверх шести бэкендов Playerok."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import BASE_URLS, BEARER_SERVICES, FEATURE_FLAGS_URL, Service
from ..common.utils import drop_none, encode_multipart, format_path, unwrap_envelope
from ..exceptions import AuthRequiredError
from .http import HttpTransport

__all__ = ["RestTransport"]


class RestTransport:
    """Маршрутизация REST-запросов по сервисам.

    Путь задаётся шаблоном с фигурными скобками, как в исходниках фронта:
    `rest.post(Service.PUBLIC, "/item/{id}/republish", path={"id": item_id})`.
    """

    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    @property
    def http(self) -> HttpTransport:
        return self._http

    def url(self, service: Service, path: str, path_params: dict[str, Any] | None = None) -> str:
        base = BASE_URLS[service].rstrip("/")
        return base + format_path(path, path_params)

    async def request(
        self,
        method: str,
        service: Service,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        json: Any = None,
        form: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
        auth: bool = False,
        unwrap: bool = True,
    ) -> Any:
        """Выполнить REST-запрос.

        `json` — обычное JSON-тело, `form` и `files` — multipart: его требуют
        `/deals/create`, `/steam/*`, `/chats/uncensor-message` и другие ручки,
        отвечающие 415 на application/json.

        `auth=True` означает, что без токена идти бессмысленно — такой вызов
        падает сразу, не тратя сетевой round-trip на заведомый 401.
        """
        if auth and not self._http.token:
            raise AuthRequiredError(f"{method} {path}")

        merged = dict(headers or {})
        if service in BEARER_SERVICES and self._http.token:
            merged.setdefault("Authorization", f"Bearer {self._http.token}")

        content: bytes | None = None
        if form is not None or files:
            content, content_type = encode_multipart(drop_none(form or {}), files)
            merged["Content-Type"] = content_type

        payload = await self._http.request(
            method,
            self.url(service, path, path_params),
            params=drop_none(params) if params else None,
            json=json,
            content=content,
            headers=merged or None,
        )
        return unwrap_envelope(payload) if unwrap else payload

    async def get(self, service: Service, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", service, path, **kwargs)

    async def post(self, service: Service, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", service, path, **kwargs)

    async def put(self, service: Service, path: str, **kwargs: Any) -> Any:
        return await self.request("PUT", service, path, **kwargs)

    async def patch(self, service: Service, path: str, **kwargs: Any) -> Any:
        return await self.request("PATCH", service, path, **kwargs)

    async def delete(self, service: Service, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", service, path, **kwargs)

    # --- feature-flags ---------------------------------------------------

    async def feature_flags(self, keys: list[str]) -> dict[str, Any]:
        """Прочитать feature-флаги площадки (flagr).

        Через них фронт узнаёт, например, актуальный адрес WebSocket
        (`ws-url`) и будущий адрес REST (`api-url`).
        """
        payload = await self._http.request(
            "POST",
            FEATURE_FLAGS_URL,
            json={"flagKeys": keys, "entityContext": {}},
        )
        results = (payload or {}).get("evaluationResults") or {}
        return results if isinstance(results, dict) else {}

    async def flag_value(self, key: str) -> Any:
        """Вернуть `variantAttachment` включённого флага или None."""
        result = (await self.feature_flags([key])).get(key) or {}
        if result.get("variantKey") in (None, "off"):
            return None
        return result.get("variantAttachment")
