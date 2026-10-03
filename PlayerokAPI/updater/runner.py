"""Запасной источник событий на поллинге.

Нужен там, где WebSocket недоступен: за прокси без апгрейда соединения,
в окружениях с обрывом долгих соединений. Даёт события чатов и сообщений,
остальные типы через поллинг не выводятся.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from ..exceptions import AuthRequiredError, PlayerokError
from ..types import ChatMessage
from .events import ChatEvent, Event, EventType, MessageEvent

if TYPE_CHECKING:
    from ..account import Account

__all__ = ["PollingRunner"]

logger = logging.getLogger("PlayerokAPI.runner")


class PollingRunner:
    """Опрашивает список чатов и выдаёт новые сообщения.

    Первый проход только запоминает состояние: события пойдут с того,
    что появилось после запуска. `replay_existing=True` отключает это
    и отдаёт последнее сообщение каждого чата сразу.
    """

    def __init__(
        self,
        account: Account,
        *,
        interval: float = 5.0,
        chats_per_tick: int = 20,
        messages_per_chat: int = 20,
        replay_existing: bool = False,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval должен быть положительным")
        self._account = account
        self._interval = interval
        self._chats_per_tick = chats_per_tick
        self._messages_per_chat = messages_per_chat
        self._replay_existing = replay_existing
        self._last_message: dict[str, str] = {}
        self._seeded = False
        self._running = False

    async def events(self) -> AsyncIterator[Event]:
        """Бесконечный поток событий. Останавливается через `stop()`."""
        if self._running:
            raise PlayerokError("Поллинг уже запущен")
        if not self._account.token:
            raise AuthRequiredError("поллинг событий")

        self._running = True
        try:
            while self._running:
                try:
                    for event in await self._tick():
                        yield event
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("Проход поллинга не удался: %s", exc)
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.sleep(self._interval)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> list[Event]:
        page = await self._account.chats.search(first=self._chats_per_tick)
        seeding = not self._seeded and not self._replay_existing
        events: list[Event] = []

        for chat in page.items:
            last = chat.last_message
            if last is None:
                continue
            previous = self._last_message.get(chat.id)
            if previous == last.id:
                continue
            self._last_message[chat.id] = last.id
            if seeding:
                continue

            events.append(ChatEvent(type=EventType.CHAT_UPDATED, raw=chat.raw, chat=chat))
            for message in await self._new_messages(chat.id, previous, last.id):
                events.append(
                    MessageEvent(type=EventType.NEW_MESSAGE, raw=message.raw, message=message)
                )

        self._seeded = True
        return events

    async def _new_messages(
        self, chat_id: str, previous: str | None, latest: str
    ) -> list[ChatMessage]:
        """Сообщения чата, появившиеся после `previous`."""
        page = await self._account.chats.messages(chat_id, limit=self._messages_per_chat)
        messages = sorted(page.items, key=lambda m: (m.created_at is None, m.created_at))
        if previous is None:
            return [m for m in messages if m.id == latest]
        tail: list[ChatMessage] = []
        for message in reversed(messages):
            if message.id == previous:
                break
            tail.append(message)
        return list(reversed(tail))
