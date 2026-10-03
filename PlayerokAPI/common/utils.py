"""Мелочи, которые нужны везде."""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import UUID

__all__ = [
    "RateLimiter",
    "backoff_delays",
    "drop_none",
    "encode_multipart",
    "format_path",
    "parse_datetime",
    "parse_uuid",
    "to_float",
    "to_int",
    "unwrap_envelope",
]

T = TypeVar("T")

_TRAILING_Z = re.compile(r"Z$", re.IGNORECASE)


def parse_datetime(value: Any) -> datetime | None:
    """Разобрать ISO-8601 из ответа API.

    Площадка отдаёт и `2026-10-03T08:50:15Z`, и миллисекунды, и голые
    epoch-таймстемпы в подписках. Всё приводится к aware-datetime в UTC.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(_TRAILING_Z.sub("+00:00", value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_uuid(value: Any) -> str | None:
    """Нормализовать UUID к строке, не падая на мусоре."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str) and value:
        return value
    return None


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def drop_none(data: Mapping[str, Any]) -> dict[str, Any]:
    """Выкинуть ключи со значением None.

    GraphQL-инпуты площадки различают «не передали» и «передали null»,
    поэтому опциональные аргументы вычищаются перед отправкой.
    """
    return {key: value for key, value in data.items() if value is not None}


def unwrap_envelope(payload: Any) -> Any:
    """Развернуть конверт `{"success": true, "data": ...}`.

    Часть REST-ручек (fragment, steam) отвечает именно так, часть — голым
    объектом. Остальное возвращается как есть.
    """
    if (
        isinstance(payload, dict)
        and payload.keys() <= {"success", "data", "message"}
        and "data" in payload
        and payload.get("success") is not False
    ):
        return payload["data"]
    return payload


def format_path(template: str, params: Mapping[str, Any] | None) -> str:
    """Подставить path-параметры в шаблон вида `/item/{id}/republish`."""
    if "{" not in template:
        return template
    values = params or {}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise KeyError(f"Не передан path-параметр {name!r} для {template!r}")
        from urllib.parse import quote

        return quote(str(values[name]), safe="")

    return re.sub(r"\{([^{}]+)\}", replace, template)


def backoff_delays(attempts: int, base: float = 0.5, cap: float = 8.0) -> Iterable[float]:
    """Экспоненциальные паузы между повторами."""
    for attempt in range(attempts):
        yield min(cap, base * (2**attempt))


def encode_multipart(
    fields: Mapping[str, Any],
    files: Mapping[str, tuple[str, bytes, str]] | None = None,
) -> tuple[bytes, str]:
    """Собрать тело multipart/form-data и вернуть его вместе с Content-Type.

    Часть ручек Playerok принимает только multipart и отвечает 415 на JSON:
    `/deals/create`, `/steam/*`, `/chats/uncensor-message`,
    `/funds-protection/send-email-code`. httpx переходит в multipart лишь
    при непустом `files`, поэтому тело собирается вручную.
    """
    import secrets

    crlf = "\r\n"
    boundary = secrets.token_hex(16)
    chunks: list[bytes] = []

    for name, value in fields.items():
        if value is None:
            continue
        header = f'--{boundary}{crlf}Content-Disposition: form-data; name="{name}"{crlf}{crlf}'
        chunks.append(header.encode() + _render_field(value) + crlf.encode())

    for name, (filename, content, content_type) in (files or {}).items():
        header = (
            f"--{boundary}{crlf}"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"{crlf}'
            f"Content-Type: {content_type}{crlf}{crlf}"
        )
        chunks.append(header.encode() + content + crlf.encode())

    chunks.append(f"--{boundary}--{crlf}".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _render_field(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bool):
        return b"true" if value else b"false"
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, ensure_ascii=False).encode()
    return str(value).encode()


class RateLimiter:
    """Ограничитель частоты запросов.

    Простое скользящее окно: не больше `rate` запросов за `period` секунд.
    Нужен, чтобы бот не выгребал 429 на пачке запросов.
    """

    def __init__(self, rate: int, period: float = 1.0) -> None:
        if rate <= 0:
            raise ValueError("rate должен быть больше нуля")
        self._rate = rate
        self._period = period
        self._hits: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                cutoff = now - self._period
                self._hits = [hit for hit in self._hits if hit > cutoff]
                if len(self._hits) < self._rate:
                    self._hits.append(now)
                    return
                await asyncio.sleep(self._hits[0] - cutoff)
