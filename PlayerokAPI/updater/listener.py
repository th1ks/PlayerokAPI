"""Слушатель событий: подписки по WebSocket и диспетчеризация обработчиков."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any

from ..exceptions import AuthRequiredError, PlayerokError
from .events import Event, EventType
from .subscriptions import SUBSCRIPTIONS, Subscription

if TYPE_CHECKING:
    from ..account import Account

__all__ = ["Listener"]

logger = logging.getLogger("PlayerokAPI.listener")

Handler = Callable[[Event], Any | Awaitable[Any]]


class Listener:
    """Собирает события всех подписок в одну очередь.

    Фильтры подписок задаются при создании: часть из них сервер требует
    обязательными (`ChatMessageWSFilter!`, `ItemDealFilter!`), но пустой
    объект подходит — выдача и так ограничена сессией токена.

    .. code-block:: python

        listener = Listener(account)

        @listener.on(EventType.NEW_MESSAGE)
        async def on_message(event):
            ...

        await listener.run()
    """

    def __init__(
        self,
        account: Account,
        *,
        events: Iterable[EventType] | None = None,
        filters: Mapping[EventType, Mapping[str, Any]] | None = None,
        resolve_url: bool = True,
    ) -> None:
        self._account = account
        self._filters = {key: dict(value) for key, value in (filters or {}).items()}
        self._resolve_url = resolve_url
        self._handlers: dict[EventType, list[Handler]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

        wanted = set(events) if events is not None else None
        self._subscriptions = tuple(
            sub for sub in SUBSCRIPTIONS if wanted is None or sub.event_type in wanted
        )

    # --- регистрация обработчиков ---------------------------------------

    def on(self, *event_types: EventType) -> Callable[[Handler], Handler]:
        """Декоратор: повесить обработчик на один или несколько типов событий."""
        if not event_types:
            raise ValueError("Укажите хотя бы один тип события")

        def decorator(handler: Handler) -> Handler:
            for event_type in event_types:
                self.add_handler(event_type, handler)
            return handler

        return decorator

    def add_handler(self, event_type: EventType, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def remove_handler(self, event_type: EventType, handler: Handler) -> None:
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    # --- жизненный цикл --------------------------------------------------

    async def run(self) -> None:
        """Слушать события и вызывать обработчики, пока не остановят."""
        async for event in self.events():
            await self._dispatch(event)

    async def events(self) -> AsyncIterator[Event]:
        """Поток событий для своего цикла обработки."""
        if self._running:
            raise PlayerokError("Слушатель уже запущен")
        if not self._account.token:
            raise AuthRequiredError("подписки")

        await self._prepare_url()
        self._running = True
        self._tasks = [
            asyncio.create_task(self._pump(sub), name=f"playerok-sub-{sub.operation}")
            for sub in self._subscriptions
        ]
        try:
            while self._running:
                yield await self._queue.get()
        finally:
            await self.stop()

    async def stop(self) -> None:
        self._running = False
        tasks, self._tasks = self._tasks, []
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def __aenter__(self) -> Listener:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    # --- внутреннее ------------------------------------------------------

    async def _prepare_url(self) -> None:
        """Спросить актуальный адрес подписок у feature-флага."""
        if not self._resolve_url:
            return
        try:
            url = await self._account.misc.websocket_url()
        except Exception as exc:
            logger.debug("Не удалось прочитать флаг ws-url: %s", exc)
            return
        if url:
            self._account.ws.url = url

    def _variables(self, sub: Subscription) -> dict[str, Any]:
        variables: dict[str, Any] = {}
        explicit = self._filters.get(sub.event_type)
        if explicit is not None:
            variables["filter"] = dict(explicit)
        elif "filter" in sub.required_variables:
            variables["filter"] = {}
        return variables

    async def _pump(self, sub: Subscription) -> None:
        try:
            stream = self._account.ws.subscribe(
                sub.document,
                self._variables(sub),
                operation_name=sub.operation,
            )
            async for data in stream:
                payload = data.get(sub.root)
                if isinstance(payload, dict):
                    self._queue.put_nowait(sub.build(sub.event_type, payload))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Подписка %s остановлена: %s", sub.operation, exc)

    async def _dispatch(self, event: Event) -> None:
        for handler in self._handlers.get(event.type, []):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Обработчик %s упал на событии %s", handler, event.type)
