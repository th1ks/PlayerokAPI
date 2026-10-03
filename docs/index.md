# PlayerokAPI

Лёгкая асинхронная библиотека для работы с API маркетплейса
[Playerok](https://playerok.com).

:::{warning}
Неофициальная библиотека. Проект не связан с Playerok и не поддерживается
площадкой. Схема API может измениться без предупреждения.
:::

Из зависимостей только `httpx` и `websockets`. Весь публичный код
типизирован, ввод-вывод асинхронный.

```bash
pip install PlayerokAPI
```

```python
import asyncio
from PlayerokAPI import Account


async def main() -> None:
    async with Account(token="ваш_token_из_cookie") as acc:
        me = await acc.get_me()
        print(me.username, me.balance.available)


asyncio.run(main())
```

## Как устроено

Площадка живёт на трёх транспортах, и библиотека использует все три,
пряча это за единым фасадом {class}`~PlayerokAPI.Account`.

| Транспорт | Что закрывает |
|---|---|
| REST `playerok.com/rest-api/public`, `bff.playerok.com`, `sapi.playerok.com` | авторизация, профиль, файлы, PL-токены, Fragment, Steam, лотереи, создание сделки |
| REST `api.playerok.com/v1/catalog` | публичный каталог: популярное и официальный магазин |
| GraphQL `playerok.com/graphql` | товары, чаты, сообщения, сделки, отзывы, транзакции |
| WebSocket `wss://ws.playerok.com/graphql` | события в реальном времени |

Где у площадки есть REST — библиотека идёт в REST. Админские и внутренние
ручки сознательно не реализованы: только то, чем пользуется обычный клиент.

```{toctree}
:caption: Руководство
:maxdepth: 2

guide/quickstart
guide/auth
guide/catalog
guide/chats
guide/deals
guide/payments
guide/events
guide/errors
guide/transports
```

```{toctree}
:caption: Справочник
:maxdepth: 2

api/index
```

## Ссылки

- [Репозиторий](https://github.com/th1ks/PlayerokAPI)
- [PyPI](https://pypi.org/project/PlayerokAPI/)
- [Телеграм-чат](https://t.me/playerokapi)
- [Задачи и предложения](https://github.com/th1ks/PlayerokAPI/issues)
