# Транспорты

Обычно к ним обращаться не нужно — {class}`~PlayerokAPI.Account` всё
разводит сам. Эта страница нужна, если вы дёргаете ручку, которой
в библиотеке ещё нет.

## Что где лежит

```python
acc.http  # HttpTransport — httpx, токен, ретраи, лимит частоты
acc.rest  # RestTransport — маршрутизация по REST-бэкендам
acc.graphql  # GraphQLTransport — запросы, мутации, загрузка файлов
acc.ws  # WebSocketTransport — подписки
```

## REST-бэкенды

Перечислены в {class}`~PlayerokAPI.common.endpoints.Service`:

| Значение | База | Авторизация |
|---|---|---|
| `PUBLIC` | `https://playerok.com/rest-api/public` | cookie `token` |
| `BFF` | `https://bff.playerok.com/rest-api/public` | `Authorization: Bearer` |
| `AUTH` | `https://sapi.playerok.com` | cookie `token` |
| `CATALOG` | `https://api.playerok.com` | не требуется |

Токен живёт в cookie-джаре на домене `.playerok.com`, поэтому уходит
во все поддомены сразу. Для BFF он дополнительно кладётся в заголовок —
этим занимается сам транспорт.

## Свой REST-запрос

```python
from PlayerokAPI.common.endpoints import Service

data = await acc.rest.get(
    Service.PUBLIC,
    "/item/{id}/testimonial-stat",
    path_params={"id": item_id},
    auth=True,
)
```

Путь задаётся шаблоном с фигурными скобками, как в исходниках фронта.
`auth=True` означает «без токена идти бессмысленно» — такой вызов
падает сразу с {exc}`~PlayerokAPI.exceptions.AuthRequiredError`.

Конверт `{"success": true, "data": ...}`, в котором отвечает часть
ручек, разворачивается автоматически. Отключается через `unwrap=False`.

### multipart

Некоторые ручки принимают только `multipart/form-data` и отвечают `415`
на JSON. Для них есть `form=`:

```python
await acc.rest.post(
    Service.PUBLIC,
    "/chats/uncensor-message",
    form={"messageId": message_id, "clickedFragment": fragment},
    auth=True,
)
```

Файлы — отдельным аргументом `files={"имя": (filename, content, mime)}`.

## Свой GraphQL-запрос

```python
data = await acc.graphql.execute(
    "query Viewer { viewer { id username } }",
    operation_name="Viewer",
    auth=True,
)
print(data["viewer"]["username"])
```

Непустой `errors` в ответе превращается в
{exc}`~PlayerokAPI.exceptions.GraphQLError`.

Мутации со скаляром `Upload` уходят по спецификации
graphql-multipart-request:

```python
from PlayerokAPI.transport import Upload

await acc.graphql.execute(
    "mutation CreateItem($input: CreateItemInput!, $attachments: [Upload!]) { ... }",
    {"input": {...}, "attachments": [None]},
    operation_name="CreateItem",
    uploads={"attachments.0": Upload.from_path("pic.png")},
    auth=True,
)
```

Ключ `uploads` — путь к месту переменной, куда сервер подставит файл.

## Своя подписка

```python
stream = acc.ws.subscribe(
    "subscription ChatUpdated($filter: ChatFilter) { chatUpdated(filter: $filter) { id } }",
    {"filter": {}},
    operation_name="ChatUpdated",
)
async for data in stream:
    print(data["chatUpdated"]["id"])
```

Прерывание итерации корректно закрывает подписку на сервере.

## Feature-флаги

```python
flags = await acc.misc.feature_flags(["ws-url", "api-url"])
url = await acc.misc.websocket_url()
```

## Общий httpx-клиент

Если библиотека должна жить в одном пуле с остальным приложением:

```python
import httpx
from PlayerokAPI import Account

async with httpx.AsyncClient() as client:
    acc = Account(token="...", client=client)
    ...
```

Переданный клиент библиотека не закрывает — это ваша забота.
