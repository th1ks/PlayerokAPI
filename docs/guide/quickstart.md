# Быстрый старт

## Установка

```bash
pip install PlayerokAPI
```

Python 3.10 и новее.

## Токен

Единственный секрет — cookie `token`, которую выдаёт веб-сессия Playerok.
Проще всего взять её в браузере: DevTools → Application → Cookies →
`https://playerok.com` → значение `token`.

Тот же токен библиотека сама подставляет и в cookie, и в заголовок
`Authorization` для BFF — разбираться, куда что идёт, не нужно.

:::{tip}
Храните токен в переменной окружения, а не в коде. Токен даёт полный
доступ к аккаунту, включая вывод средств.
:::

```python
import os
from PlayerokAPI import Account

acc = Account(token=os.environ["PLAYEROK_TOKEN"])
```

## Контекстный менеджер

`Account` держит HTTP-пул и, если вы слушаете события, WebSocket-соединение.
Закрывать их нужно явно — для этого есть `async with`:

```python
import asyncio
from PlayerokAPI import Account


async def main() -> None:
    async with Account(token="...") as acc:
        me = await acc.get_me()
        print(me.username)


asyncio.run(main())
```

Без `async with` вызовите `await acc.aclose()` сами.

## Без токена

Часть API публичная и работает анонимно: каталог, конфигурация Fragment,
ставки кэшбэка, лотереи, гео.

```python
async with Account() as acc:
    for item in await acc.items.top(page_size=5):
        print(item.price, item.name)
```

Методы, которым токен обязателен, падают с
{exc}`~PlayerokAPI.exceptions.AuthRequiredError` сразу, не тратя запрос
на заведомый `401`.

## Настройки клиента

```python
acc = Account(
    token="...",
    timeout=20.0,  # таймаут одного запроса
    retries=3,  # повторы на сетевых сбоях, 429 и 5xx
    rate_limit=(5, 1.0),  # не больше 5 запросов в секунду
    proxy="http://127.0.0.1:8080",
    user_agent="MyBot/1.0",
)
```

`POST` после `5xx` не повторяется — чтобы повтор не создал вторую покупку.

Если нужен свой `httpx.AsyncClient` — передайте его в `client=`; тогда
закрывать его тоже вам.

## Пагинация

Выборки курсорные и возвращают {class}`~PlayerokAPI.Page`:

```python
page = await acc.items.search(query="steam", first=20)
print(page.total_count, page.has_next_page)

for item in page:
    print(item.name)

if page.has_next_page:
    page = await acc.items.search(query="steam", first=20, after=page.end_cursor)
```

## Неизвестные поля

Площадка меняет схему без предупреждения, поэтому разбор ответов терпимый:
неизвестные поля не ломают модель, а незнакомое значение перечисления
сохраняется как есть.

```python
status = ItemStatus("СОВЕРШЕННО_НОВЫЙ_СТАТУС")
status.value  # 'СОВЕРШЕННО_НОВЫЙ_СТАТУС'
status.is_known  # False
```

Исходный словарь ответа всегда лежит в поле `raw` — туда можно залезть
за тем, чего библиотека ещё не знает:

```python
item = await acc.items.get(slug="cool-account")
item.raw["someBrandNewField"]
```
