"""Каналы уведомлений и привязка Telegram-бота."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from ..common.utils import drop_none
from ..enums import NotificationProviderId
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport
from ..types import NotificationChannel

__all__ = ["NotificationsMethods"]

_CHANNEL = "id name description enabled props"

_LIST = f"""
query NotificationProviders($userId: UUID!) {{
    notificationProviders(userId: $userId) {{ {_CHANNEL} }}
}}
"""
_ENABLE = f"""
mutation EnableNotificationProvider($input: EnableNotificationProviderInput!) {{
    enableNotificationProvider(input: $input) {{ {_CHANNEL} }}
}}
"""
_DISABLE = f"""
mutation DisableNotificationProvider($input: DisableNotificationProviderInput!) {{
    disableNotificationProvider(input: $input) {{ {_CHANNEL} }}
}}
"""
_BOT_LINK = "query GetTelegramBotLink { getTelegramBotLink { subscribeURL } }"
_GENERATE_BOT_LINK = """
mutation GenerateTelegramBotLink { generateTelegramBotLink { subscribeURL } }
"""


class NotificationsMethods:
    """Почта, Telegram, push и прочие каналы.

    `user_id` по умолчанию берётся у текущего аккаунта, так что в обычном
    случае его передавать не нужно.
    """

    def __init__(
        self,
        graphql: GraphQLTransport,
        resolve_user_id: Callable[[], Awaitable[str]],
    ) -> None:
        self._graphql = graphql
        self._resolve_user_id = resolve_user_id

    async def channels(self, *, user_id: str | None = None) -> list[NotificationChannel]:
        """Все каналы и их состояние."""
        data = await self._graphql.execute(
            _LIST,
            {"userId": user_id or await self._resolve_user_id()},
            operation_name="NotificationProviders",
            auth=True,
        )
        providers = data.get("notificationProviders")
        if not isinstance(providers, list):
            raise PlayerokError("Пустой или неожиданный ответ notificationProviders")
        return [NotificationChannel.from_dict(item) for item in providers if isinstance(item, dict)]

    async def enable(
        self,
        provider: NotificationProviderId | str,
        *,
        props: Mapping[str, Any] | None = None,
        user_id: str | None = None,
    ) -> NotificationChannel:
        """Включить канал."""
        body = drop_none(
            {
                "providerId": str(provider),
                "userId": user_id or await self._resolve_user_id(),
                "props": dict(props) if props else None,
            }
        )
        data = await self._graphql.execute(
            _ENABLE, {"input": body}, operation_name="EnableNotificationProvider", auth=True
        )
        return NotificationChannel.from_dict(_object(data, "enableNotificationProvider"))

    async def disable(
        self,
        provider: NotificationProviderId | str,
        *,
        user_id: str | None = None,
    ) -> NotificationChannel:
        """Выключить канал."""
        body = {
            "providerId": str(provider),
            "userId": user_id or await self._resolve_user_id(),
        }
        data = await self._graphql.execute(
            _DISABLE, {"input": body}, operation_name="DisableNotificationProvider", auth=True
        )
        return NotificationChannel.from_dict(_object(data, "disableNotificationProvider"))

    async def telegram_bot_link(self) -> str:
        """Ссылка на Telegram-бота для уведомлений."""
        data = await self._graphql.execute(
            _BOT_LINK, operation_name="GetTelegramBotLink", auth=True
        )
        return _subscribe_url(data, "getTelegramBotLink")

    async def generate_telegram_bot_link(self) -> str:
        """Выпустить новую ссылку: старая после этого перестаёт работать."""
        data = await self._graphql.execute(
            _GENERATE_BOT_LINK, operation_name="GenerateTelegramBotLink", auth=True
        )
        return _subscribe_url(data, "generateTelegramBotLink")


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value


def _subscribe_url(data: dict[str, Any], key: str) -> str:
    url = _object(data, key).get("subscribeURL")
    if not isinstance(url, str) or not url:
        raise PlayerokError("Сервер не вернул ссылку на бота")
    return url
