"""Розыгрыши площадки."""

from __future__ import annotations

import uuid
from typing import Any

from ..common.endpoints import Service
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport

__all__ = ["LotteryMethods"]


class LotteryMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def active(self) -> dict[str, Any] | None:
        """Текущий розыгрыш или None, если ни один не идёт."""
        payload = await self._rest.get(Service.PUBLIC, "/lottery/active")
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ активного розыгрыша")
        return payload

    async def pools(self, lottery_id: str) -> Any:
        """Призовые пулы розыгрыша."""
        return await self._rest.get(
            Service.PUBLIC,
            "/lottery/{lotteryId}/pools",
            path_params={"lotteryId": lottery_id},
        )

    async def winners(self, lottery_id: str) -> Any:
        """Победители всех пулов."""
        return await self._rest.get(
            Service.PUBLIC,
            "/lottery/{lotteryId}/winners",
            path_params={"lotteryId": lottery_id},
        )

    async def pool_winners(self, lottery_id: str, pool_id: str) -> Any:
        """Победители одного пула."""
        return await self._rest.get(
            Service.PUBLIC,
            "/lottery/{lotteryId}/pools/{poolId}/winners",
            path_params={"lotteryId": lottery_id, "poolId": pool_id},
        )

    async def telegram_url(self, lottery_id: str) -> Any:
        """Ссылка на Telegram-канал розыгрыша."""
        return await self._rest.get(
            Service.PUBLIC,
            "/lottery/{lotteryId}/telegram-url",
            path_params={"lotteryId": lottery_id},
            auth=True,
        )

    async def telegram_subscription(self, lottery_id: str) -> Any:
        """Подтверждена ли подписка на канал."""
        return await self._rest.get(
            Service.PUBLIC,
            "/lottery/{lotteryId}/telegram-subscription",
            path_params={"lotteryId": lottery_id},
            auth=True,
        )

    async def buy_tickets(
        self,
        lottery_id: str,
        pool_id: str,
        quantity: int,
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        """Купить билеты.

        Ключ идемпотентности уходит в заголовке `idempotency-key`: повтор
        того же запроса не спишет деньги дважды. Если не задать — создаётся
        новый, и тогда повтор будет новой покупкой.
        """
        if quantity < 1:
            raise ValueError("Количество билетов должно быть не меньше 1")
        return await self._rest.post(
            Service.PUBLIC,
            "/lottery/{lotteryId}/pools/{poolId}/tickets",
            path_params={"lotteryId": lottery_id, "poolId": pool_id},
            json={"quantity": quantity},
            headers={"idempotency-key": idempotency_key or str(uuid.uuid4())},
            auth=True,
        )

    async def claim_daily(self, lottery_id: str) -> Any:
        """Забрать ежедневный билет."""
        return await self._rest.post(
            Service.PUBLIC,
            "/lottery/{lotteryId}/daily-claims/claim",
            path_params={"lotteryId": lottery_id},
            json={},
            auth=True,
        )

    async def claim_social(self, lottery_id: str, platform: str) -> Any:
        """Забрать билет за подписку на соцсеть."""
        if not platform:
            raise ValueError("Нужна платформа")
        return await self._rest.post(
            Service.PUBLIC,
            "/lottery/{lotteryId}/social-claims/claim",
            path_params={"lotteryId": lottery_id},
            json={"platform": platform},
            auth=True,
        )
