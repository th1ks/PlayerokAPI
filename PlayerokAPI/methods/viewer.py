"""Профиль текущего пользователя."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport
from ..types import User, UserBalance

__all__ = ["ViewerMethods"]


class ViewerMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def get_me(self) -> User:
        """Получить профиль и доступный баланс."""
        payload = await self._rest.get(Service.BFF, "/viewer", auth=True)
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ /viewer")
        user = User.from_dict(payload)
        if user.balance is None:
            user.balance = await self.get_balance()
        return user

    async def get_balance(self) -> UserBalance:
        payload = await self._rest.get(Service.BFF, "/viewer/balance", auth=True)
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ /viewer/balance")
        return UserBalance.from_dict(payload)

    async def is_username_taken(self, username: str) -> bool:
        payload = await self._rest.get(
            Service.PUBLIC,
            "/viewer/username-availability",
            params={"username": username},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("isTaken"), bool):
            raise PlayerokError("Неожиданный ответ проверки имени")
        return payload["isTaken"]

    async def register_username(self, username: str) -> User:
        payload = await self._rest.post(
            Service.BFF,
            "/viewer/registration",
            json={"username": username},
            auth=True,
        )
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ регистрации")
        return User.from_dict(payload)

    async def set_avatar(self, avatar_id: str) -> dict[str, Any]:
        """Привязать уже загруженный файл к профилю."""
        payload = await self._rest.put(
            Service.BFF,
            "/viewer/avatar",
            json={"avatarId": avatar_id},
            auth=True,
        )
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ обновления аватара")
        return payload
