"""Все события аккаунта в консоль. Запасной режим — поллинг.

python examples/events.py
PLAYEROK_POLLING=1 python examples/events.py
"""

from __future__ import annotations

import asyncio
import contextlib
import os

from PlayerokAPI import Account, DealEvent, Event, EventType, MessageEvent


def describe(event: Event) -> str:
    if isinstance(event, MessageEvent) and event.message:
        author = event.message.user.username if event.message.user else "система"
        return f"{author}: {event.message.text or '[без текста]'}"
    if isinstance(event, DealEvent) and event.deal:
        name = event.deal.item.name if event.deal.item else "—"
        return f"{event.deal.status} · {name}"
    return ""


async def main() -> None:
    token = os.environ["PLAYEROK_TOKEN"]
    use_polling = bool(os.environ.get("PLAYEROK_POLLING"))

    async with Account(token=token) as acc:
        source = acc.polling(interval=5.0) if use_polling else acc.listener()
        print("Источник:", "поллинг" if use_polling else "WebSocket")

        async for event in source.events():
            line = describe(event)
            print(f"[{event.received_at:%H:%M:%S}] {event.type}" + (f"  {line}" if line else ""))

            if event.type is EventType.BALANCE_UPDATED and event.raw:
                print("   новый баланс:", event.raw.get("available"))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
