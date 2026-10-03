# Чаты и сообщения

## Список чатов

```python
page = await acc.chats.search(first=20)
for chat in page:
    last = chat.last_message.text if chat.last_message else ""
    print(chat.id, chat.unread_messages_counter, last)
```

Фильтр соответствует `ChatFilter`:

```python
await acc.chats.search(filter={"unread": True, "type": "PM"})
await acc.chats.search(filter={"bookmarked": True})
```

## Собеседник

У личного диалога двое участников, и чтобы найти второго, нужен свой
идентификатор:

```python
me = await acc.get_me()
chat = await acc.chats.get(chat_id)
companion = chat.companion(me.id)
print(companion.username if companion else "—")
```

## Сообщения

```python
page = await acc.chats.messages(chat_id, limit=30)
for message in page:
    print(message.created_at, message.user.username if message.user else "система")
    print(" ", message.text)
```

Пагинация двусторонняя: `after` листает вперёд, `before` — назад.
Указывать оба сразу нельзя.

## Отправка

```python
await acc.chats.send(chat_id, "Здравствуйте!")
```

Картинки можно отправить двумя путями. Либо передать файлы, и библиотека
загрузит их во временное хранилище сама:

```python
from PlayerokAPI.transport import Upload

await acc.chats.send(
    chat_id,
    "Вот скриншот",
    images=[Upload.from_path("screen.png")],
)
```

Либо, если файлы уже загружены, передать их идентификаторы:

```python
await acc.chats.send(chat_id, image_ids=[file_id])
```

Сообщение должно содержать текст или хотя бы одну картинку.

## Прочитано

```python
await acc.chats.mark_read(chat_id)
```

## Системные сообщения

Площадка шлёт в чат события: начало диалога, подтверждение телефона,
начисление PL-токенов. У такого сообщения заполнено `event`, а автора
может не быть вовсе.

```python
if message.is_system:
    print("событие:", message.event)
else:
    print(message.user.username, message.text)
```

Своё сообщение от чужого в боте удобно отличать по `author_id`:

```python
if message.author_id == me.id:
    return
```
