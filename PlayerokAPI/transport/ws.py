"""WebSocket-транспорт подписок: протокол `graphql-transport-ws`."""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json as jsonlib
import logging
import random
from collections.abc import AsyncIterator, Coroutine
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from ..common.endpoints import TOKEN_COOKIE, WEB_ORIGIN, WS_URL
from ..exceptions import GraphQLError, WebSocketError
from .http import HttpTransport

__all__ = ["WebSocketTransport"]

logger = logging.getLogger("PlayerokAPI.ws")

_ACK_TIMEOUT = 15.0


class _Subscription:
    __slots__ = ("id", "payload", "queue")

    def __init__(self, sub_id: str, payload: dict[str, Any]) -> None:
        self.id = sub_id
        self.payload = payload
        self.queue: asyncio.Queue[Any] = asyncio.Queue()


class WebSocketTransport:
    """Мультиплексор подписок с автопереподключением.

    Все подписки живут на одном соединении. При обрыве соединение
    поднимается заново и активные подписки переоформляются — вызывающий
    код об этом не узнаёт, его итератор просто продолжает отдавать события.
    """

    def __init__(
        self,
        http: HttpTransport,
        url: str = WS_URL,
        *,
        ping_interval: float = 25.0,
        reconnect: bool = True,
        max_reconnect_delay: float = 30.0,
    ) -> None:
        self._http = http
        self._url = url
        self._ping_interval = ping_interval
        self._reconnect = reconnect
        self._max_reconnect_delay = max_reconnect_delay

        self._conn: ClientConnection | None = None
        self._reader: asyncio.Task[None] | None = None
        self._subs: dict[str, _Subscription] = {}
        self._ids = itertools.count(1)
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        self._url = value

    @property
    def connected(self) -> bool:
        return self._conn is not None

    # --- публичный интерфейс --------------------------------------------

    async def subscribe(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Открыть подписку и отдавать `data` каждого события.

        Итератор бесконечен, пока подписка жива. Прерывание итерации
        (`break`, отмена задачи) корректно закрывает подписку на сервере.
        """
        await self._ensure_connected()

        sub = _Subscription(
            str(next(self._ids)),
            {
                "query": query,
                "variables": variables or {},
                "operationName": operation_name,
            },
        )
        self._subs[sub.id] = sub
        await self._send({"id": sub.id, "type": "subscribe", "payload": sub.payload})

        try:
            while True:
                item = await sub.queue.get()
                if item is None:
                    return
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            self._subs.pop(sub.id, None)
            if self._conn is not None:
                with contextlib.suppress(Exception):
                    await self._send({"id": sub.id, "type": "complete"})

    async def close(self) -> None:
        self._closed = True
        for sub in list(self._subs.values()):
            sub.queue.put_nowait(None)
        self._subs.clear()
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()
        await self._drop_connection()

    async def __aenter__(self) -> WebSocketTransport:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # --- соединение ------------------------------------------------------

    async def _ensure_connected(self) -> None:
        if self._closed:
            raise WebSocketError("Транспорт подписок уже закрыт")
        async with self._lock:
            if self._conn is not None:
                return
            await self._connect()

    async def _connect(self) -> None:
        headers = {
            "Origin": WEB_ORIGIN,
            "User-Agent": self._http.client.headers.get("User-Agent", ""),
        }
        if self._http.token:
            headers["Cookie"] = f"{TOKEN_COOKIE}={self._http.token}"

        try:
            conn = await connect(
                self._url,
                subprotocols=["graphql-transport-ws"],  # type: ignore[list-item]
                additional_headers=headers,
                ping_interval=self._ping_interval,
                ping_timeout=self._ping_interval,
                max_size=8 * 1024 * 1024,
            )
        except Exception as exc:
            raise WebSocketError(f"Не удалось подключиться к {self._url}: {exc}") from exc

        await conn.send(jsonlib.dumps({"type": "connection_init", "payload": self._init_params()}))
        try:
            raw = await asyncio.wait_for(conn.recv(), timeout=_ACK_TIMEOUT)
        except (TimeoutError, asyncio.TimeoutError) as exc:
            await conn.close()
            raise WebSocketError("Сервер не прислал connection_ack") from exc

        message = _loads(raw)
        if message.get("type") != "connection_ack":
            await conn.close()
            raise WebSocketError(f"Ожидался connection_ack, пришло {message.get('type')!r}")

        self._conn = conn
        self._reader = asyncio.create_task(self._read_loop(conn), name="playerok-ws-reader")
        logger.debug("Подписки подключены к %s", self._url)

    def _init_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "x-gql-op": "ws-subscription",
            "x-gql-path": "PlayerokAPI",
            "x-timezone-offset": 0,
        }
        if self._http.token:
            params["token"] = self._http.token
        return params

    def _spawn(self, coro: Coroutine[Any, Any, Any], name: str) -> None:
        """Фоновая задача с удержанием ссылки, чтобы её не собрал GC."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _send(self, message: dict[str, Any]) -> None:
        conn = self._conn
        if conn is None:
            raise WebSocketError("Нет соединения с подписками")
        await conn.send(jsonlib.dumps(message))

    async def _drop_connection(self) -> None:
        reader, self._reader = self._reader, None
        conn, self._conn = self._conn, None
        if reader is not None and reader is not asyncio.current_task():
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader
        if conn is not None:
            with contextlib.suppress(Exception):
                await conn.close()

    # --- чтение ----------------------------------------------------------

    async def _read_loop(self, conn: ClientConnection) -> None:
        try:
            async for raw in conn:
                self._dispatch(_loads(raw))
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as exc:
            logger.debug("Соединение подписок закрыто: %s", exc)
        except Exception as exc:
            logger.warning("Сбой чтения подписок: %s", exc)

        if self._closed or self._conn is not conn:
            return
        self._conn = None
        self._reader = None
        if self._reconnect and self._subs:
            self._spawn(self._reconnect_loop(), "playerok-ws-reconnect")
        else:
            self._fail_all(WebSocketError("Соединение с подписками разорвано"))

    def _dispatch(self, message: dict[str, Any]) -> None:
        kind = message.get("type")
        if kind == "ping":
            if self._conn is not None:
                self._spawn(self._send({"type": "pong"}), "playerok-ws-pong")
            return
        if kind in (None, "pong", "connection_ack"):
            return

        sub = self._subs.get(str(message.get("id")))
        if sub is None:
            return

        if kind == "next":
            payload = message.get("payload") or {}
            errors = payload.get("errors")
            if errors:
                sub.queue.put_nowait(GraphQLError(errors, sub.payload.get("operationName")))
                return
            data = payload.get("data")
            if data is not None:
                sub.queue.put_nowait(data)
        elif kind == "error":
            payload = message.get("payload")
            errors = payload if isinstance(payload, list) else [{"message": str(payload)}]
            sub.queue.put_nowait(GraphQLError(errors, sub.payload.get("operationName")))
        elif kind == "complete":
            sub.queue.put_nowait(None)

    def _fail_all(self, error: Exception) -> None:
        for sub in self._subs.values():
            sub.queue.put_nowait(error)

    async def _reconnect_loop(self) -> None:
        delay = 1.0
        while not self._closed and self._subs:
            await asyncio.sleep(delay + random.uniform(0, 0.5))
            try:
                async with self._lock:
                    if self._conn is None:
                        await self._connect()
                for sub in list(self._subs.values()):
                    await self._send({"id": sub.id, "type": "subscribe", "payload": sub.payload})
            except Exception as exc:
                logger.debug("Переподключение не удалось: %s", exc)
                delay = min(self._max_reconnect_delay, delay * 2)
                continue
            logger.info("Подписки восстановлены (%s шт.)", len(self._subs))
            return


def _loads(raw: str | bytes) -> dict[str, Any]:
    try:
        message = jsonlib.loads(raw)
    except ValueError as exc:
        raise WebSocketError(f"Некорректный кадр: {raw!r}") from exc
    return message if isinstance(message, dict) else {}
