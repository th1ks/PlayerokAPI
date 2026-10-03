"""Fragment: покупка звёзд Telegram."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport

__all__ = ["FragmentMethods"]


class FragmentMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def config(self) -> dict[str, Any]:
        """Цена звезды, границы покупки и доступность сервиса."""
        payload = await self._rest.get(Service.PUBLIC, "/fragment/config")
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ конфигурации Fragment")
        return payload

    async def deposits_count(self) -> int:
        """Сколько покупок звёзд проведено за всё время."""
        payload = await self._rest.get(Service.PUBLIC, "/fragment/deposits/count")
        if not isinstance(payload, int):
            raise PlayerokError("Неожиданный ответ счётчика покупок")
        return payload

    async def deposit(self, deposit_id: str) -> Any:
        """Одна покупка по идентификатору."""
        return await self._rest.get(
            Service.PUBLIC,
            "/fragment/deposits/{id}",
            path_params={"id": deposit_id},
            auth=True,
        )

    async def deposit_logs(self, deposit_id: str) -> Any:
        """Журнал статусов покупки."""
        return await self._rest.get(
            Service.PUBLIC,
            "/fragment/deposits/{id}/logs",
            path_params={"id": deposit_id},
            auth=True,
        )

    async def validate_username(self, username: str) -> Any:
        """Проверить, что на этот ник Telegram можно отправить звёзды."""
        if not username:
            raise ValueError("Пустой ник")
        return await self._rest.post(
            Service.PUBLIC,
            "/fragment/validate-username",
            json={"username": username},
        )

    async def buy(self, username: str, stars_amount: int) -> Any:
        """Купить звёзды с баланса Playerok."""
        _check(username, stars_amount)
        return await self._rest.post(
            Service.PUBLIC,
            "/fragment/buy",
            json={"username": username, "starsAmount": stars_amount},
            auth=True,
        )

    async def buy_external(
        self,
        username: str,
        stars_amount: int,
        provider_id: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Купить звёзды внешней оплатой, минуя баланс."""
        _check(username, stars_amount)
        if not provider_id:
            raise ValueError("Нужен provider_id")
        body = dict(extra or {})
        body.update(
            drop_none(
                {
                    "username": username,
                    "starsAmount": stars_amount,
                    "providerId": provider_id,
                }
            )
        )
        return await self._rest.post(Service.PUBLIC, "/fragment/buy-external", json=body)


def _check(username: str, stars_amount: int) -> None:
    if not username:
        raise ValueError("Пустой ник")
    if stars_amount < 1:
        raise ValueError("Количество звёзд должно быть положительным")
