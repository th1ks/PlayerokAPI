"""Пополнение кошелька Steam."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..enums import TransactionProvider
from ..transport.rest import RestTransport

__all__ = ["SteamMethods"]


class SteamMethods:
    """Ручки этого раздела принимают только multipart — отсюда `form=`."""

    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def currency_rate(self, from_currency: str, to_currency: str | None = None) -> Any:
        """Курс конвертации для пополнения."""
        if not from_currency:
            raise ValueError("Нужна исходная валюта")
        return await self._rest.get(
            Service.PUBLIC,
            "/steam/currency-rate",
            params=drop_none({"from": from_currency, "to": to_currency}),
        )

    async def check_payment_possibility(self, account: str) -> Any:
        """Можно ли пополнить этот аккаунт Steam."""
        if not account:
            raise ValueError("Нужен логин аккаунта Steam")
        return await self._rest.get(
            Service.PUBLIC,
            "/steam/check-payment-posibility",
            params={"account": account},
        )

    async def check_promocode(self, promocode: str) -> Any:
        """Проверить промокод на пополнение."""
        if not promocode:
            raise ValueError("Пустой промокод")
        return await self._rest.post(
            Service.PUBLIC,
            "/steam/check-promocode",
            form={"promocode": promocode},
        )

    async def create_deposit(
        self,
        provider: TransactionProvider | str,
        value: float,
        *,
        account: str | None = None,
        promocode: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Создать пополнение с баланса Playerok."""
        return await self._create(
            "/steam/create-deposit", provider, value, account, promocode, extra
        )

    async def create_deposit_external(
        self,
        provider: TransactionProvider | str,
        value: float,
        *,
        account: str | None = None,
        promocode: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Создать пополнение внешней оплатой."""
        return await self._create(
            "/steam/create-deposit-external", provider, value, account, promocode, extra
        )

    async def _create(
        self,
        path: str,
        provider: TransactionProvider | str,
        value: float,
        account: str | None,
        promocode: str | None,
        extra: dict[str, Any] | None,
    ) -> Any:
        if value <= 0:
            raise ValueError("Сумма должна быть положительной")
        body = dict(extra or {})
        body.update(
            drop_none(
                {
                    "provider": str(provider),
                    "value": value,
                    "account": account,
                    "promocode": promocode,
                }
            )
        )
        return await self._rest.post(Service.PUBLIC, path, form=body, auth=True)
