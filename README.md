# PlayerokAPI

Лёгкая асинхронная библиотека для работы с API маркетплейса [Playerok](https://playerok.com).

[![CI](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml)
[![Docs](https://app.readthedocs.org/projects/playerok-api/badge/?version=latest)](https://playerok-api.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/PlayerokAPI.svg)](https://pypi.org/project/PlayerokAPI/)
[![Python](https://img.shields.io/pypi/pyversions/PlayerokAPI.svg)](https://pypi.org/project/PlayerokAPI/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-чат-26A5E4?logo=telegram&logoColor=white)](https://t.me/playerokapi)

> Неофициальная библиотека. Проект не связан с Playerok и не поддерживается площадкой.

## Что это

Клиент к Playerok по образцу `FunPayAPI`: пакет-папка, который можно поставить из PyPI
или положить рядом с ботом. Внутри — асинхронный клиент, типизированные модели
и слушатель событий. Из зависимостей только `httpx` и `websockets`.

## Установка

```bash
pip install PlayerokAPI
```

## Быстрый старт

```python
import asyncio
from PlayerokAPI import Account


async def main() -> None:
    async with Account(token="ваш_token_из_cookie") as acc:
        me = await acc.get_me()
        print(me.username, me.balance.available)

        chats = await acc.chats.search(filter={"unread": True}, first=10)
        for chat in chats:
            print(chat.id, chat.last_message.text if chat.last_message else "")


asyncio.run(main())
```

Часть API публичная и работает без токена:

```python
async with Account() as acc:
    for item in await acc.items.top(page_size=5):
        print(item.price, item.name)
```

## События

```python
import asyncio
from PlayerokAPI import Account, EventType, MessageEvent


async def main() -> None:
    async with Account(token="...") as acc:
        me = await acc.get_me()
        listener = acc.listener(events=[EventType.NEW_MESSAGE])

        @listener.on(EventType.NEW_MESSAGE)
        async def on_message(event: MessageEvent) -> None:
            message = event.message
            if message.is_system or message.author_id == me.id:
                return
            await acc.send_message(message.chat_id, "Привет!")

        await listener.run()


asyncio.run(main())
```

Типы событий: `NEW_MESSAGE`, `MESSAGE_EDITED`, `MESSAGE_DELETED`, `NEW_CHAT`,
`CHAT_UPDATED`, `CHAT_READ`, `NEW_DEAL`, `DEAL_UPDATED`, `ITEM_CREATED`,
`ITEM_UPDATED`, `ITEM_REMOVED`, `NEW_TRANSACTION`, `BALANCE_UPDATED`.

Падение обработчика логируется и не роняет ни цикл, ни соседние обработчики.
Если WebSocket в вашем окружении недоступен, есть поллинг с тем же интерфейсом:

```python
async for event in acc.polling(interval=5.0).events():
    print(event.type)
```

## Разделы API

| Неймспейс | Что внутри |
|---|---|
| `acc.auth` | вход по коду на почту, второй фактор, выход |
| `acc.viewer` | профиль, баланс, аватар, настройки, двухфакторная аутентификация |
| `acc.games` | игры, категории |
| `acc.items` | поиск, топ, официальный магазин, создание, публикация, тарифы, продвижение |
| `acc.chats` | чаты, сообщения, картинки, отметка о прочтении |
| `acc.deals` | сделки, покупка, смена статуса, жалоба на проблему |
| `acc.testimonials` | отзывы |
| `acc.transactions` | история транзакций, вывод средств |
| `acc.payments` | пополнение баланса, провайдеры, способы оплаты, карты |
| `acc.notifications` | каналы уведомлений, привязка Telegram-бота |
| `acc.files` | загрузка файлов в хранилище |
| `acc.pl_tokens` | баланс, история, кэшбэк, промокоды |
| `acc.fragment` | покупка Telegram Stars |
| `acc.steam` | пополнение кошелька Steam |
| `acc.lottery` | розыгрыши и билеты |
| `acc.misc` | гео, баннеры, feature-флаги, код защиты средств |

## Пополнение баланса

```python
providers = await acc.payments.providers()
for provider in providers:
    print(provider.id, provider.name, provider.fee, provider.incoming)

url = await acc.payments.create_payment_url(
    1000,
    "SBP",
    payment_method="RUB",
    email="mail@example.com",
)
print(url)  # платёжная страница провайдера
```

Результат придёт событием `NEW_TRANSACTION`.

## Где взять токен

DevTools → Application → Cookies → `https://playerok.com` → значение cookie `token`.

Либо через код на почту:

```python
async with Account() as acc:
    await acc.auth.send_otp("mail@example.com")
    result = await acc.auth.confirm_otp("mail@example.com", "123456")
    print(acc.token)  # при включённой 2FA сначала acc.auth.confirm_second_factor(...)
```

## Обработка ошибок

Всё наследуется от `PlayerokError`:

```python
from PlayerokAPI import HTTPError, PlayerokError, RateLimitError, UnauthorizedError

try:
    await acc.items.get(slug="nope")
except UnauthorizedError:
    ...  # токен протух
except RateLimitError as exc:
    ...  # exc.retry_after
except HTTPError as exc:
    print(exc.status_code, exc.message)
except PlayerokError:
    ...
```

Сетевые сбои, `429` и `5xx` на идемпотентных методах повторяются автоматически.
`POST` после `5xx` не повторяется — чтобы не создать вторую покупку.

## Документация

Полное руководство и справочник API — [playerok-api.readthedocs.io](https://playerok-api.readthedocs.io).

## Примеры

- [`examples/catalog.py`](examples/catalog.py) — публичный каталог без токена
- [`examples/profile.py`](examples/profile.py) — профиль, баланс, продажи
- [`examples/autoresponder.py`](examples/autoresponder.py) — автоответчик в чатах
- [`examples/events.py`](examples/events.py) — поток событий, WebSocket и поллинг

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
└── updater/          события, слушатель, поллинг
```

## Где спросить

Телеграм-чат библиотеки — [@playerokapi](https://t.me/playerokapi).
Баги и предложения лучше в [issues](https://github.com/th1ks/PlayerokAPI/issues).

## Лицензия

[MIT](LICENSE)
