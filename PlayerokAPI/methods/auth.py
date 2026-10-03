"""Вход по e-mail и управление сессией."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..common.endpoints import TOKEN_COOKIE, Service
from ..common.utils import unwrap_envelope
from ..exceptions import PlayerokError, TokenError
from ..transport.rest import RestTransport

__all__ = ["AuthMethods", "OtpResult"]


@dataclass
class OtpResult:
    """Результат OTP: готовый токен либо сессия для второго фактора."""

    token: str | None = field(default=None, repr=False)
    requires_two_factor: bool = False
    #: Сессия второго фактора как её отдал сервер: строка либо объект.
    second_factor_session: Any = field(default=None, repr=False)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def second_factor_token(self) -> str | None:
        """Токен сессии 2FA для `confirm_second_factor`.

        Форму поля площадка не документирует, поэтому поддержаны оба
        варианта: голая строка и объект с токеном внутри.
        """
        session = self.second_factor_session
        if isinstance(session, str):
            return session or None
        if isinstance(session, dict):
            for key in ("token", "sessionToken", "secondFactorSession", "id"):
                value = session.get(key)
                if isinstance(value, str) and value:
                    return value
        return None


class AuthMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def send_otp(self, email: str) -> None:
        """Отправить одноразовый код на e-mail."""
        await self._rest.post(Service.PUBLIC, "/auth/send-otp", json={"email": email})

    async def confirm_otp(self, email: str, code: str) -> OtpResult:
        """Подтвердить код и сохранить токен либо вернуть сессию 2FA."""
        payload, cookie_token = await self._post_for_token(
            "/auth/confirm-otp",
            {"email": email, "otpCode": code},
        )
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ подтверждения OTP")
        if payload.get("requiresTwoFactor"):
            result = OtpResult(
                requires_two_factor=True,
                second_factor_session=payload.get("secondFactorSession"),
                raw=payload,
            )
            if result.second_factor_token is None:
                raise PlayerokError("Сервер не вернул сессию второго фактора")
            return result
        token = self._save_token(payload, cookie_token)
        return OtpResult(token=token, raw=payload)

    async def confirm_second_factor(self, session: str | OtpResult, code: str) -> str:
        """Завершить вход по шестизначному коду 2FA.

        Принимает и сам токен сессии, и результат `confirm_otp` целиком.
        """
        token = session.second_factor_token if isinstance(session, OtpResult) else session
        if not token:
            raise ValueError("Нужен токен сессии второго фактора")
        payload, cookie_token = await self._post_for_token(
            "/auth/confirm-second-factor",
            {"token": token, "totpCode": code},
        )
        return self._save_token(payload, cookie_token)

    async def logout(self) -> None:
        """Закрыть сессию на сервере и удалить локальный токен."""
        await self._rest.post(Service.BFF, "/auth/logout", auth=True)
        self._rest.http.token = None

    async def _post_for_token(self, path: str, body: dict[str, str]) -> tuple[Any, str | None]:
        response = await self._rest.http.raw_request(
            "POST", self._rest.url(Service.PUBLIC, path), json=body
        )
        try:
            payload = response.json() if response.content else {}
        except ValueError as exc:
            raise PlayerokError("Неожиданный ответ авторизации") from exc
        return unwrap_envelope(payload), response.cookies.get(TOKEN_COOKIE)

    def _save_token(self, payload: Any, cookie_token: str | None) -> str:
        token = payload.get("token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            token = cookie_token
        if not isinstance(token, str) or not token:
            raise TokenError("В ответе авторизации нет cookie token")
        self._rest.http.token = token
        return token
