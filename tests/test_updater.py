from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import GRAPHQL_URL
from PlayerokAPI.exceptions import AuthRequiredError
from PlayerokAPI.updater import EventType, Listener, MessageEvent, PollingRunner
from PlayerokAPI.updater.subscriptions import SUBSCRIPTIONS


class FakeWebSocket:
    """Подменяет WebSocketTransport: отдаёт заранее заданные кадры."""

    def __init__(self, frames: dict[str, list[dict[str, Any]]]) -> None:
        self.frames = frames
        self.url = "wss://stub/graphql"
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def subscribe(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        self.calls.append((operation_name or "", dict(variables or {})))
        for frame in self.frames.get(operation_name or "", []):
            yield frame
        # Подписка живёт, пока её не отменят.
        await asyncio.Event().wait()

    async def close(self) -> None:
        return None


@pytest.fixture
async def acc() -> Account:
    account = Account(token="tok", retries=0)
    yield account
    await account.aclose()


# --- документы подписок --------------------------------------------------


def test_every_event_type_has_a_subscription() -> None:
    covered = {sub.event_type for sub in SUBSCRIPTIONS}
    assert covered == set(EventType)


def test_subscription_documents_are_well_formed() -> None:
    for sub in SUBSCRIPTIONS:
        assert sub.document.startswith(f"subscription {sub.operation}")
        assert sub.root in sub.document
        assert sub.document.count("{") == sub.document.count("}")


# --- слушатель -----------------------------------------------------------


async def test_listener_dispatches_to_handler(acc: Account) -> None:
    acc.ws = FakeWebSocket(  # type: ignore[assignment]
        {
            "chatMessageCreated": [
                {"chatMessageCreated": {"id": "m1", "text": "привет", "user": {"id": "u2"}}}
            ]
        }
    )
    listener = Listener(acc, events=[EventType.NEW_MESSAGE], resolve_url=False)
    seen: list[MessageEvent] = []

    @listener.on(EventType.NEW_MESSAGE)
    async def handler(event: MessageEvent) -> None:
        seen.append(event)

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.05)
    await listener.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(seen) == 1
    assert seen[0].type is EventType.NEW_MESSAGE
    assert seen[0].text == "привет"


async def test_listener_passes_empty_required_filter(acc: Account) -> None:
    ws = FakeWebSocket({})
    acc.ws = ws  # type: ignore[assignment]
    listener = Listener(acc, events=[EventType.NEW_MESSAGE, EventType.NEW_CHAT], resolve_url=False)

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.05)
    await listener.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    sent = dict(ws.calls)
    # ChatMessageWSFilter обязателен — уходит пустым объектом.
    assert sent["chatMessageCreated"] == {"filter": {}}
    # ChatFilter необязателен — не передаём вовсе.
    assert sent["chatCreated"] == {}


async def test_listener_uses_explicit_filter(acc: Account) -> None:
    ws = FakeWebSocket({})
    acc.ws = ws  # type: ignore[assignment]
    listener = Listener(
        acc,
        events=[EventType.NEW_MESSAGE],
        filters={EventType.NEW_MESSAGE: {"chatId": "ch1"}},
        resolve_url=False,
    )

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.05)
    await listener.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert dict(ws.calls)["chatMessageCreated"] == {"filter": {"chatId": "ch1"}}


async def test_failing_handler_does_not_stop_the_others(acc: Account) -> None:
    acc.ws = FakeWebSocket(  # type: ignore[assignment]
        {"chatMessageCreated": [{"chatMessageCreated": {"id": "m1", "text": "x"}}]}
    )
    listener = Listener(acc, events=[EventType.NEW_MESSAGE], resolve_url=False)
    reached: list[str] = []

    @listener.on(EventType.NEW_MESSAGE)
    async def broken(event: MessageEvent) -> None:
        raise RuntimeError("упал")

    @listener.on(EventType.NEW_MESSAGE)
    async def healthy(event: MessageEvent) -> None:
        reached.append(event.message.id if event.message else "")

    task = asyncio.create_task(listener.run())
    await asyncio.sleep(0.05)
    await listener.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert reached == ["m1"]


async def test_listener_requires_token() -> None:
    account = Account(token=None)
    try:
        listener = Listener(account, resolve_url=False)
        with pytest.raises(AuthRequiredError):
            await listener.run()
    finally:
        await account.aclose()


def test_on_requires_event_type(acc: Account) -> None:
    listener = Listener(acc, resolve_url=False)
    with pytest.raises(ValueError):
        listener.on()


# --- поллинг -------------------------------------------------------------


def _chats_response(last_message_id: str, text: str) -> dict[str, Any]:
    return {
        "data": {
            "chats": {
                "edges": [
                    {
                        "node": {
                            "id": "ch1",
                            "type": "PM",
                            "lastMessage": {"id": last_message_id, "text": text},
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False},
                "totalCount": 1,
            }
        }
    }


def _messages_response(ids: list[str]) -> dict[str, Any]:
    return {
        "data": {
            "chatMessages": {
                "edges": [
                    {
                        "node": {
                            "id": mid,
                            "text": mid,
                            "createdAt": f"2026-10-0{i + 1}T00:00:00Z",
                        }
                    }
                    for i, mid in enumerate(ids)
                ],
                "pageInfo": {"hasNextPage": False},
                "totalCount": len(ids),
            }
        }
    }


@respx.mock
async def test_polling_seeds_first_then_emits(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json=_chats_response("m1", "первое")),
        httpx.Response(200, json=_chats_response("m2", "второе")),
        httpx.Response(200, json=_messages_response(["m1", "m2"])),
    ]

    runner = PollingRunner(acc, interval=0.01)
    collected = []
    async for event in runner.events():
        collected.append(event)
        if len(collected) == 2:
            runner.stop()
            break

    assert [e.type for e in collected] == [EventType.CHAT_UPDATED, EventType.NEW_MESSAGE]
    assert collected[1].message.id == "m2"


@respx.mock
async def test_polling_replays_existing_when_asked(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json=_chats_response("m1", "первое")),
        httpx.Response(200, json=_messages_response(["m1"])),
    ]

    runner = PollingRunner(acc, interval=0.01, replay_existing=True)
    collected = []
    async for event in runner.events():
        collected.append(event)
        if len(collected) == 2:
            runner.stop()
            break

    assert collected[1].type is EventType.NEW_MESSAGE
    assert collected[1].message.id == "m1"


async def test_polling_requires_token() -> None:
    account = Account(token=None)
    try:
        runner = PollingRunner(account)
        with pytest.raises(AuthRequiredError):
            async for _ in runner.events():
                break
    finally:
        await account.aclose()


def test_polling_validates_interval(acc: Account) -> None:
    with pytest.raises(ValueError):
        PollingRunner(acc, interval=0)


async def test_listener_reports_startup(acc: Account, caplog) -> None:  # type: ignore[no-untyped-def]
    """Молчание слушателя должно быть отличимо от поломки."""
    acc.ws = FakeWebSocket({})  # type: ignore[assignment]
    listener = Listener(acc, events=[EventType.NEW_MESSAGE], resolve_url=False)

    with caplog.at_level("INFO", logger="PlayerokAPI.listener"):
        task = asyncio.create_task(listener.run())
        await asyncio.sleep(0.05)
        await listener.stop()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert "chatMessageCreated" in caplog.text
    assert "1 подписку" in caplog.text
