"""PL-токены: баланс, история, кэшбэк, промокоды."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport

__all__ = ["PlTokensMethods"]


class PlTokensMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def balance(self) -> Any:
        """Сколько PL-токенов на счету."""
        return await self._rest.get(Service.PUBLIC, "/pl-tokens/balance", auth=True)

    async def history(self, *, limit: int | None = None, cursor: str | None = None) -> Any:
        """История начислений и списаний."""
        return await self._rest.get(
            Service.PUBLIC,
            "/pl-tokens/history",
            params=drop_none({"limit": limit, "cursor": cursor}) or None,
            auth=True,
        )

    async def cashback_config(self) -> dict[str, Any]:
        """Ставки кэшбэка: по маркетплейсу, Steam, Fragment и официальному магазину."""
        payload = await self._rest.get(Service.PUBLIC, "/pl-tokens/cashback-config")
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ конфигурации кэшбэка")
        return payload

    async def apply_promo_code(self, code: str) -> Any:
        """Активировать промокод на PL-токены."""
        if not code:
            raise ValueError("Пустой промокод")
        return await self._rest.post(
            Service.PUBLIC,
            "/pl-tokens/promo-code",
            json={"code": code},
            auth=True,
        )
