# PlayerokAPI

Лёгкая асинхронная библиотека для работы с API маркетплейса [Playerok](https://playerok.com).

[![CI](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/th1ks/PlayerokAPI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Неофициальная библиотека. Проект никак не связан с Playerok и не поддерживается площадкой.

## Что это

`PlayerokAPI` — клиент к Playerok по образцу `FunPayAPI`: пакет-папка, который можно и
положить рядом с ботом или установить из исходников. Сейчас готовы транспорты,
типизированные модели, вход по OTP и методы профиля. Остальные модули и слушатель
событий в разработке.

Площадка использует REST, GraphQL и WebSocket; библиотека поддерживает все три:

- **REST** (`/rest-api/public`, `bff.playerok.com`, `sapi.playerok.com`,
  `api.playerok.com`) — новый API. Авторизация, профиль, файлы, PL-токены,
  лотереи, Fragment, Steam, создание сделки и отдельные ручки каталога.
- **GraphQL** (`playerok.com/graphql`) — каталог, чаты, сообщения, сделки, отзывы, транзакции.
- **WebSocket** (`wss://ws.playerok.com/graphql`) — события в реальном времени.

Где у площадки есть REST — библиотека идёт в REST.

## Установка

```bash
pip install -e .
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


asyncio.run(main())
```

## Где взять токен

DevTools → Application → Cookies → `https://playerok.com` → значение cookie `token`.

Либо через e-mail OTP прямо из библиотеки:

```python
from PlayerokAPI import Account

async with Account() as acc:
    await acc.auth.send_otp("mail@example.com")
    result = await acc.auth.confirm_otp("mail@example.com", code="123456")
    if result.requires_two_factor:
        session = result.second_factor_session
        assert session is not None
        token = await acc.auth.confirm_second_factor(session["token"], "654321")
    else:
        token = result.token
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
└── methods/          модули API: auth, viewer
```

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
Пулл-реквесты идут в `develop`.

## Лицензия

[MIT](LICENSE)
