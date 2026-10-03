# Ошибки

Всё, что кидает библиотека, наследуется от
{exc}`~PlayerokAPI.exceptions.PlayerokError` — одного `except` хватит,
чтобы не выпустить наружу ничего неожиданного.

```text
PlayerokError
├── AuthRequiredError      метод требует токен, а его нет
├── TokenError             токен не прошёл проверку
├── NetworkError           запрос не доехал
│   └── RequestTimeoutError
├── HTTPError              ответ с кодом ошибки
│   ├── BadRequestError    400
│   ├── UnauthorizedError  401
│   ├── ForbiddenError     403
│   ├── NotFoundError      404
│   ├── ConflictError      409
│   ├── RateLimitError     429
│   └── ServerError        5xx
├── GraphQLError           непустой errors в ответе GraphQL
└── WebSocketError         сбой соединения подписок
```

## Разбор

```python
from PlayerokAPI import (
    HTTPError,
    PlayerokError,
    RateLimitError,
    UnauthorizedError,
)

try:
    item = await acc.items.get(slug="nope")
except UnauthorizedError:
    ...  # токен протух, нужен новый
except RateLimitError as exc:
    await asyncio.sleep(exc.retry_after or 5)
except HTTPError as exc:
    print(exc.status_code, exc.message, exc.payload)
except PlayerokError:
    ...
```

У {exc}`~PlayerokAPI.exceptions.HTTPError` есть `status_code`, `url`,
`payload` с разобранным телом и `message` — текст, вытащенный из тела.
Площадка отдаёт ошибки в двух формах, `{"statusCode", "message",
"errors": [...]}` и `{"error", "message", "statusCode"}`, обе
разбираются одинаково.

## GraphQL

```python
from PlayerokAPI import GraphQLError

try:
    await acc.deals.get(deal_id)
except GraphQLError as exc:
    print(exc.code)  # extensions.code первой ошибки
    print(exc.errors)  # весь список
```

## Повторы

Сетевые сбои, `429` и `5xx` на идемпотентных методах повторяются сами,
с экспоненциальной паузой; `Retry-After` уважается. `POST` после `5xx`
**не** повторяется — чтобы повтор не создал вторую покупку.

Число попыток задаётся при создании клиента:

```python
acc = Account(token="...", retries=5)
acc = Account(token="...", retries=0)  # вообще без повторов
```

## Проверки до запроса

Часть ошибок библиотека ловит на месте, не тратя сетевой вызов:

```python
await acc.items.search(first=0)  # ValueError
await acc.chats.send(chat_id)  # ValueError: нет ни текста, ни картинок
await acc.pl_tokens.apply_promo_code("ABC")  # AuthRequiredError без токена
```
