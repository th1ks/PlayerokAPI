# События

События приходят по WebSocket на `wss://ws.playerok.com/graphql`
протоколом `graphql-transport-ws`. Все подписки мультиплексируются
в одно соединение; при обрыве оно поднимается заново, а подписки
переоформляются — вызывающий код об этом не узнаёт.

## Обработчики

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

Один обработчик можно повесить на несколько типов:

```python
@listener.on(EventType.NEW_DEAL, EventType.DEAL_UPDATED)
async def on_deal(event): ...
```

Обработчик может быть и обычной функцией, не корутиной. Исключение
внутри него логируется и не роняет ни цикл, ни соседние обработчики.

## Событие приходит только на новое

`NEW_MESSAGE` срабатывает в момент, когда собеседник пишет. Уже лежащие
в чатах и непрочитанные сообщения слушатель не повторяет — поэтому сразу
после запуска он молчит, и это нормально.

Чтобы отличить работающий слушатель от сломанного, включите лог: на старте
он пишет, сколько подписок открыл.

```python
import logging

logging.basicConfig(level=logging.INFO)
```

```text
INFO PlayerokAPI.listener: Слушаю 1 подписку: chatMessageCreated
```

Если подписка отвалится, там же появится предупреждение. Когда нужно
обработать и то, что накопилось до запуска, берите поллинг с
`replay_existing=True` — он отдаст последнее сообщение каждого чата.

## Свой цикл

Если декораторы не нужны, события можно читать напрямую:

```python
async for event in acc.listener().events():
    print(event.type, event.received_at)
```

## Типы событий

| Тип | Класс события | Полезная нагрузка |
|---|---|---|
| `NEW_MESSAGE` | {class}`~PlayerokAPI.MessageEvent` | `event.message` |
| `MESSAGE_EDITED` | {class}`~PlayerokAPI.MessageEvent` | `event.message` |
| `MESSAGE_DELETED` | {class}`~PlayerokAPI.MessageEvent` | `event.message` |
| `NEW_CHAT` | {class}`~PlayerokAPI.ChatEvent` | `event.chat` |
| `CHAT_UPDATED` | {class}`~PlayerokAPI.ChatEvent` | `event.chat` |
| `CHAT_READ` | {class}`~PlayerokAPI.ChatEvent` | `event.chat` |
| `NEW_DEAL` | {class}`~PlayerokAPI.DealEvent` | `event.deal` |
| `DEAL_UPDATED` | {class}`~PlayerokAPI.DealEvent` | `event.deal` |
| `ITEM_CREATED` | {class}`~PlayerokAPI.ItemEvent` | `event.item` |
| `ITEM_UPDATED` | {class}`~PlayerokAPI.ItemEvent` | `event.item` |
| `ITEM_REMOVED` | {class}`~PlayerokAPI.ItemEvent` | `event.item` |
| `NEW_TRANSACTION` | {class}`~PlayerokAPI.TransactionEvent` | `event.transaction` |
| `BALANCE_UPDATED` | {class}`~PlayerokAPI.BalanceUpdatedEvent` | `event.balance` |

У каждого события есть `type`, `received_at` и `raw` — исходная
нагрузка от сервера.

## Фильтры подписок

Часть подписок в схеме требует фильтр обязательным. По умолчанию
библиотека шлёт пустой объект: выдача и так ограничена сессией токена.
Сузить можно явно:

```python
listener = acc.listener(
    events=[EventType.NEW_MESSAGE],
    filters={EventType.NEW_MESSAGE: {"chatId": chat_id}},
)
```

## Адрес соединения

На старте слушатель читает feature-флаг `ws-url` и берёт адрес оттуда,
чтобы переезд площадки не требовал обновления библиотеки. Если флаг
недоступен, остаётся адрес по умолчанию. Отключается аргументом
`resolve_url=False` у {class}`~PlayerokAPI.Listener`.

## Поллинг

Там, где WebSocket недоступен — за прокси без апгрейда соединения,
в окружениях с обрывом долгих соединений, — есть запасной источник
с тем же интерфейсом:

```python
runner = acc.polling(interval=5.0)
async for event in runner.events():
    print(event.type)
```

Он опрашивает список чатов, сравнивает `lastMessage` и догружает то,
что появилось. Из типов отдаёт только `CHAT_UPDATED` и `NEW_MESSAGE`.

Первый проход только запоминает состояние — события пойдут с того, что
появилось после запуска. Чтобы получить и текущее последнее сообщение
каждого чата, создайте {class}`~PlayerokAPI.PollingRunner` напрямую
с `replay_existing=True`.

## Остановка

```python
await listener.stop()  # слушатель
runner.stop()  # поллинг
```

`async with Account(...)` закрывает соединение подписок сам.
