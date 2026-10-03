"""Иерархия ошибок библиотеки."""

from __future__ import annotations

from typing import Any

__all__ = [
    "AuthRequiredError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "GraphQLError",
    "HTTPError",
    "NetworkError",
    "NotFoundError",
    "PlayerokError",
    "RateLimitError",
    "RequestTimeoutError",
    "ServerError",
    "TokenError",
    "UnauthorizedError",
    "WebSocketError",
]


class PlayerokError(Exception):
    """Базовая ошибка. Всё, что кидает библиотека, наследуется от неё."""


class AuthRequiredError(PlayerokError):
    """Метод требует токен, а он не задан."""

    def __init__(self, method: str = "") -> None:
        suffix = f" ({method})" if method else ""
        super().__init__(f"Для этого запроса нужен токен{suffix}")


class TokenError(PlayerokError):
    """Токен не прошёл проверку на стороне площадки."""


class NetworkError(PlayerokError):
    """Запрос не доехал: обрыв соединения, DNS, TLS."""


class RequestTimeoutError(NetworkError):
    """Истёк таймаут запроса."""


class HTTPError(PlayerokError):
    """Ответ с кодом ошибки.

    `payload` — разобранное тело, если это был JSON, иначе строка.
    `message` — текст ошибки, вытащенный из тела: площадка отдаёт его
    в двух формах, `{"statusCode", "message", "errors": [...]}`
    и `{"error", "message", "statusCode"}`.
    """

    def __init__(
        self,
        status_code: int,
        url: str,
        payload: Any = None,
        message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.payload = payload
        self.message = message or _extract_message(payload) or f"HTTP {status_code}"
        super().__init__(f"{status_code} {url}: {self.message}")


class BadRequestError(HTTPError):
    """400 — невалидные параметры."""


class UnauthorizedError(HTTPError):
    """401 — токен отсутствует, протух или отозван."""


class ForbiddenError(HTTPError):
    """403 — доступ запрещён."""


class NotFoundError(HTTPError):
    """404 — объекта нет."""


class ConflictError(HTTPError):
    """409 — конфликт состояния."""


class RateLimitError(HTTPError):
    """429 — слишком часто."""

    def __init__(
        self,
        status_code: int,
        url: str,
        payload: Any = None,
        message: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(status_code, url, payload, message)


class ServerError(HTTPError):
    """5xx — упало на стороне площадки."""


class GraphQLError(PlayerokError):
    """GraphQL вернул непустой `errors`."""

    def __init__(self, errors: list[dict[str, Any]], operation: str | None = None) -> None:
        self.errors = errors
        self.operation = operation
        first = errors[0] if errors else {}
        self.message = first.get("message", "Неизвестная ошибка GraphQL")
        self.code = (first.get("extensions") or {}).get("code")
        prefix = f"{operation}: " if operation else ""
        super().__init__(f"{prefix}{self.message}")


class WebSocketError(PlayerokError):
    """Ошибка соединения с подписками."""


_STATUS_MAP: dict[int, type[HTTPError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def error_for_status(
    status_code: int,
    url: str,
    payload: Any = None,
    retry_after: float | None = None,
) -> HTTPError:
    """Подобрать класс исключения под код ответа."""
    if status_code == 429:
        return RateLimitError(status_code, url, payload, retry_after=retry_after)
    cls = _STATUS_MAP.get(status_code)
    if cls is None:
        cls = ServerError if status_code >= 500 else HTTPError
    return cls(status_code, url, payload)


def _extract_message(payload: Any) -> str | None:
    if isinstance(payload, str):
        return payload.strip() or None
    if not isinstance(payload, dict):
        return None
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict) and first.get("message"):
            return str(first["message"])
    for key in ("message", "error", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None
