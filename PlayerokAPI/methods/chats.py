"""Чаты и сообщения текущего пользователя."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport, Upload
from ..types import Chat, ChatMessage, File, Page
from . import fields

__all__ = ["ChatsMethods"]

_MESSAGE_FIELDS = fields.MESSAGE
_CHAT_FIELDS = fields.CHAT
_PAGE_INFO = fields.PAGE_INFO

_SEARCH = f"""
query Chats($pagination: Pagination, $filter: ChatFilter) {{
    chats(pagination: $pagination, filter: $filter) {{
        edges {{ node {{ {_CHAT_FIELDS} }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_GET = f"""
query Chat($id: UUID!) {{ chat(id: $id) {{ {_CHAT_FIELDS} }} }}
"""
_MESSAGES = f"""
query ChatMessages($pagination: Pagination, $filter: ChatMessageFilter) {{
    chatMessages(pagination: $pagination, filter: $filter) {{
        edges {{ node {{ {_MESSAGE_FIELDS} }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_CREATE = f"""
mutation CreateChatMessage($input: CreateChatMessageInput!) {{
    createChatMessage(input: $input) {{ {_MESSAGE_FIELDS} }}
}}
"""
_UPDATE = f"""
mutation UpdateChatMessage($input: UpdateChatMessageInput!) {{
    updateChatMessage(input: $input) {{ {_MESSAGE_FIELDS} }}
}}
"""
_MARK_READ = f"""
mutation MarkChatAsRead($input: MarkChatAsReadInput!) {{
    markChatAsRead(input: $input) {{ {_CHAT_FIELDS} }}
}}
"""
_UPLOAD_IMAGE = """
mutation UploadChatImage($input: UploadTemporaryAttachmentInput!, $file: Upload!) {
    uploadChatImageIntoTemporaryStore(input: $input, file: $file) {
        id url chatId clientAttachmentId expiresAt
    }
}
"""
_REMOVE = """
mutation RemoveChatMessage($id: UUID!) {
    removeChatMessage(id: $id) { id deletedAt }
}
"""


class ChatsMethods:
    def __init__(self, graphql: GraphQLTransport) -> None:
        self._graphql = graphql

    async def search(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Page[Chat]:
        """Список чатов с фильтром `ChatFilter` и курсорной пагинацией."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _SEARCH,
            {
                "pagination": drop_none({"first": first, "after": after}),
                "filter": dict(filter) if filter else None,
            },
            operation_name="Chats",
            auth=True,
        )
        return Page.from_connection(_object(data, "chats"), Chat)

    async def get(self, chat_id: str) -> Chat:
        """Получить чат по идентификатору."""
        data = await self._graphql.execute(_GET, {"id": chat_id}, operation_name="Chat", auth=True)
        return Chat.from_dict(_object(data, "chat"))

    async def messages(
        self,
        chat_id: str,
        *,
        limit: int = 30,
        after: str | None = None,
        before: str | None = None,
        filter: Mapping[str, Any] | None = None,
    ) -> Page[ChatMessage]:
        """Сообщения чата: `after` для следующей, `before` для предыдущей страницы."""
        if limit < 1:
            raise ValueError("limit должен быть положительным")
        if after is not None and before is not None:
            raise ValueError("Укажите только один из after или before")
        pagination = (
            {"last": limit, "before": before}
            if before is not None
            else drop_none({"first": limit, "after": after})
        )
        filters = dict(filter or {})
        filters["chatId"] = chat_id
        data = await self._graphql.execute(
            _MESSAGES,
            {"pagination": pagination, "filter": filters},
            operation_name="ChatMessages",
            auth=True,
        )
        page: Page[ChatMessage] = Page.from_connection(_object(data, "chatMessages"), ChatMessage)
        for message in page.items:
            message.chat_id = chat_id
        return page

    async def upload_image(
        self, chat_id: str, image: Upload, *, client_attachment_id: str | None = None
    ) -> File:
        """Временно загрузить картинку перед отправкой сообщения."""
        data = await self._graphql.execute(
            _UPLOAD_IMAGE,
            {
                "input": {
                    "chatId": chat_id,
                    "clientAttachmentId": client_attachment_id or str(uuid4()),
                },
                "file": None,
            },
            uploads={"file": image},
            operation_name="UploadChatImage",
            auth=True,
        )
        payload = _object(data, "uploadChatImageIntoTemporaryStore")
        if not isinstance(payload.get("id"), str) or not payload["id"]:
            raise PlayerokError("Сервер не вернул идентификатор картинки")
        return File.from_dict(payload)

    async def send(
        self,
        chat_id: str,
        text: str | None = None,
        *,
        images: Sequence[Upload] = (),
        image_ids: Sequence[str] = (),
    ) -> ChatMessage:
        """Отправить текст и картинки; новые картинки загружаются заранее."""
        if not text and not images and not image_ids:
            raise ValueError("Сообщение должно содержать текст или картинки")
        ids = list(image_ids)
        for image in images:
            ids.append((await self.upload_image(chat_id, image)).id)
        body = drop_none({"chatId": chat_id, "text": text, "imagesIds": ids or None})
        data = await self._graphql.execute(
            _CREATE,
            {"input": body},
            operation_name="CreateChatMessage",
            auth=True,
        )
        return ChatMessage.from_dict(_object(data, "createChatMessage"), chat_id)

    async def edit(self, message_id: str, text: str) -> ChatMessage:
        """Изменить текст своего сообщения."""
        data = await self._graphql.execute(
            _UPDATE,
            {"input": {"id": message_id, "text": text}},
            operation_name="UpdateChatMessage",
            auth=True,
        )
        return ChatMessage.from_dict(_object(data, "updateChatMessage"))

    async def mark_read(self, chat_id: str) -> Chat:
        """Отметить сообщения чата прочитанными."""
        data = await self._graphql.execute(
            _MARK_READ,
            {"input": {"chatId": chat_id}},
            operation_name="MarkChatAsRead",
            auth=True,
        )
        return Chat.from_dict(_object(data, "markChatAsRead"))

    async def remove(self, message_id: str) -> ChatMessage:
        """Удалить своё сообщение."""
        data = await self._graphql.execute(
            _REMOVE,
            {"id": message_id},
            operation_name="RemoveChatMessage",
            auth=True,
        )
        return ChatMessage.from_dict(_object(data, "removeChatMessage"))


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
