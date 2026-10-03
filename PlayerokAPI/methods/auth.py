"""Вход по e-mail и управление сессией."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..common.endpoints import TOKEN_COOKIE, Service
from ..exceptions import PlayerokError, TokenError
from ..transport.rest import RestTransport

__all__ = ["AuthMethods", "OtpResult"]


@dataclass
class OtpResult:
    """Результат OTP: готовый токен либо сессия для второго фактора."""

    token: str | None = field(default=None, repr=False)
    requires_two_factor: bool = False
    second_factor_session: dict[str, Any] | None = field(default=None, repr=False)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


class AuthMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def send_otp(self, email: str) -> None:
        """Отправить одноразовый код на e-mail."""
        await self._rest.post(Service.PUBLIC, "/auth/send-otp", json={"email": email})

    async def confirm_otp(self, email: str, code: str) -> OtpResult:
        """Подтвердить код и сохранить токен либо вернуть сессию 2FA."""
        payload = await self._rest.post(
            Service.PUBLIC,
            "/auth/confirm-otp",
            json={"email": email, "otpCode": code},
        )
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ подтверждения OTP")
        if payload.get("requiresTwoFactor"):
            session = payload.get("secondFactorSession")
            if not isinstance(session, dict):
                raise PlayerokError("Сервер не вернул сессию второго фактора")
            return OtpResult(requires_two_factor=True, second_factor_session=session, raw=payload)
        token = self._save_token(payload)
        return OtpResult(token=token, raw=payload)

    async def confirm_second_factor(self, session_token: str, code: str) -> str:
        """Завершить вход по шестизначному коду 2FA."""
        payload = await self._rest.post(
            Service.PUBLIC,
            "/auth/confirm-second-factor",
            json={"token": session_token, "totpCode": code},
        )
        return self._save_token(payload)

    async def logout(self) -> None:
        """Закрыть сессию на сервере и удалить локальный токен."""
        await self._rest.post(Service.BFF, "/auth/logout", auth=True)
        self._rest.http.token = None

    def _save_token(self, payload: Any) -> str:
        token = payload.get("token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            candidates = [
                cookie.value
                for cookie in self._rest.http.client.cookies.jar
                if cookie.name == TOKEN_COOKIE
                and (
                    cookie.domain.lstrip(".") == "playerok.com"
                    or cookie.domain.lstrip(".").endswith(".playerok.com")
                )
            ]
            token = next(
                (candidate for candidate in candidates if candidate != self._rest.http.token), None
            )
            if not token and candidates:
                token = candidates[-1]
        if not isinstance(token, str) or not token:
            raise TokenError("В ответе авторизации нет cookie token")
        self._rest.http.token = token
        return token
