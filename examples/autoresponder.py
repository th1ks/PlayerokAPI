"""Автоответчик: здоровается в новом диалоге и отвечает на ключевые слова.

python examples/autoresponder.py
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from PlayerokAPI import Account, EventType, MessageEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

REPLIES = {
    "привет": "Привет! Чем могу помочь?",
    "цена": "Цена указана в объявлении и уже со всеми скидками.",
    "гарантия": "Гарантия действует всё время сделки — деньги у площадки.",
}


async def main() -> None:
    token = os.environ["PLAYEROK_TOKEN"]

    async with Account(token=token) as acc:
        me = await acc.get_me()
        greeted: set[str] = set()
        listener = acc.listener(events=[EventType.NEW_MESSAGE])

        @listener.on(EventType.NEW_MESSAGE)
        async def on_message(event: MessageEvent) -> None:
            message = event.message
            if message is None or message.chat_id is None:
                return
            # Свои и системные сообщения пропускаем, иначе бот ответит сам себе.
            if message.is_system or message.author_id == me.id:
                return

            text = (message.text or "").lower()
            reply = next((answer for key, answer in REPLIES.items() if key in text), None)

            if reply is None and message.chat_id not in greeted:
                reply = "Здравствуйте! Я на связи, отвечу в течение нескольких минут."

            if reply is None:
                return

            greeted.add(message.chat_id)
            await acc.send_message(message.chat_id, reply)
            await acc.chats.mark_read(message.chat_id)
            logging.info("Ответил в %s: %s", message.chat_id, reply)

        logging.info("Слушаю чаты от имени %s", me.username)
        await listener.run()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
