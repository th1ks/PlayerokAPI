"""Профиль текущего пользователя."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport
from ..types import BankCard, User, UserBalance

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

    async def config(self) -> dict[str, Any]:
        """Настройки аккаунта, которыми фронт управляет интерфейсом."""
        return _dict(await self._rest.get(Service.BFF, "/viewer/config", auth=True), "config")

    async def notifications(self) -> Any:
        """Состояние уведомлений."""
        return await self._rest.get(Service.BFF, "/viewer/notifications", auth=True)

    async def bindings(self) -> Any:
        """Привязанные способы входа: почта, соцсети, телефон."""
        return await self._rest.get(Service.BFF, "/viewer/bindings", auth=True)

    async def chosen_card(self) -> BankCard | None:
        """Карта, выбранная для выплат."""
        payload = await self._rest.get(Service.BFF, "/viewer/chosen-card", auth=True)
        return BankCard.from_dict(payload) if isinstance(payload, dict) and payload else None

    async def two_factor(self) -> Any:
        """Включена ли двухфакторная аутентификация."""
        return await self._rest.get(Service.BFF, "/viewer/two-factor", auth=True)

    async def request_two_factor_email_code(self) -> Any:
        """Шаг 1 включения 2FA: выслать код на почту."""
        return await self._rest.post(
            Service.PUBLIC,
            "/viewer/two-factor/enable/request-email-code",
            json={},
            auth=True,
        )

    async def verify_two_factor_email_code(self, code: str) -> Any:
        """Шаг 2: подтвердить код с почты. В ответе приходит токен для шага 3."""
        if not code:
            raise ValueError("Пустой код")
        return await self._rest.post(
            Service.PUBLIC,
            "/viewer/two-factor/enable/verify-email-code",
            json={"code": code},
            auth=True,
        )

    async def confirm_two_factor(self, token: str, totp_code: str) -> Any:
        """Шаг 3: подтвердить кодом из приложения-аутентификатора."""
        if not token or not totp_code:
            raise ValueError("Нужны token и totp_code")
        return await self._rest.post(
            Service.PUBLIC,
            "/viewer/two-factor/enable/confirm",
            json={"token": token, "totpCode": totp_code},
            auth=True,
        )

    async def disable_two_factor(self, **body: Any) -> Any:
        """Выключить 2FA."""
        return await self._rest.post(
            Service.PUBLIC,
            "/viewer/two-factor/disable",
            json=body or {},
            auth=True,
        )

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


def _dict(payload: Any, what: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PlayerokError(f"Неожиданный ответ {what}")
    return payload
