# PlayerokAPI

Лёгкая асинхронная библиотека для работы с API маркетплейса [Playerok](https://playerok.com).

[![CI](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/PlayerokAPI.svg)](https://pypi.org/project/PlayerokAPI/)
[![Python](https://img.shields.io/pypi/pyversions/PlayerokAPI.svg)](https://pypi.org/project/PlayerokAPI/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Неофициальная библиотека. Проект никак не связан с Playerok и не поддерживается площадкой.

## Что это

`PlayerokAPI` — клиент к Playerok по образцу `FunPayAPI`: пакет-папка, который можно и
поставить из PyPI, и положить рядом с ботом. Внутри — асинхронный клиент, типизированные
модели и слушатель событий.

Площадка живёт на двух транспортах, и библиотека использует оба:

- **REST** (`/rest-api/public`, `bff.playerok.com`, `sapi.playerok.com`) — новый API.
  Авторизация, профиль, файлы, PL-токены, лотереи, Fragment, Steam, создание сделки.
- **GraphQL** (`playerok.com/graphql`) — каталог, чаты, сообщения, сделки, отзывы, транзакции.
- **WebSocket** (`wss://ws.playerok.com/graphql`) — события в реальном времени.

Где у площадки есть REST — библиотека идёт в REST. Полная карта: [`docs/api-map.md`](docs/api-map.md).

## Установка

```bash
pip install PlayerokAPI
```

Зависимости — только `httpx` и `websockets`.

## Быстрый старт

```python
import asyncio
from PlayerokAPI import Account


async def main() -> None:
    async with Account(token="ваш_token_из_cookie") as acc:
        me = await acc.get_me()
        print(f"{me.username}: {me.balance.available} ₽")

        async for chat in acc.chats.iterate(unread=True):
            print(chat.id, chat.last_message.text if chat.last_message else "")


asyncio.run(main())
```

## Слушатель событий

```python
import asyncio
from PlayerokAPI import Account
from PlayerokAPI.updater import EventType, Listener


async def main() -> None:
    async with Account(token="...") as acc:
        listener = Listener(acc)

        @listener.on(EventType.NEW_MESSAGE)
        async def on_message(event):
            if event.message.user.id == acc.id:
                return
            await acc.chats.send_message(event.message.chat_id, "Привет!")

        await listener.run()


asyncio.run(main())
```

## Где взять токен

DevTools → Application → Cookies → `https://playerok.com` → значение cookie `token`.

Либо через e-mail OTP прямо из библиотеки:

```python
from PlayerokAPI import Account

async with Account() as acc:
    await acc.auth.send_otp("mail@example.com")
    token = await acc.auth.confirm_otp("mail@example.com", code="123456")
    print(token)
```

## Структура пакета

```
PlayerokAPI/
├── account.py        фасад Account — точка входа
├── types.py          модели данных
├── enums.py          перечисления из схемы
├── exceptions.py     иерархия ошибок
├── common/           конфигурация, эндпоинты, утилиты
├── transport/        HTTP, REST, GraphQL, WebSocket
├── methods/          модули API: auth, viewer, items, chats, deals, …
└── updater/          события и слушатель
```

## Документация

- [Карта API](docs/api-map.md) — какие бэкенды есть, что где лежит, как авторизоваться
- [Примеры](examples/)

## Разработка

```bash
git clone https://github.com/th1ks/PlayerokAPI
cd PlayerokAPI
pip install -e ".[dev]"
ruff check .
mypy PlayerokAPI
pytest
```

Ветки: `main` — релизы, `develop` — интеграционная, фичи — `feat/*`, правки — `fix/*`.
Пулл-реквесты идут в `develop`. Подробнее — [CONTRIBUTING.md](CONTRIBUTING.md).

## Лицензия

[MIT](LICENSE)
