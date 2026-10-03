"""Мелкие публичные ручки, не тянущие на отдельный модуль."""

from __future__ import annotations

from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..enums import FundsProtectionCodeType
from ..exceptions import PlayerokError
from ..transport.rest import RestTransport

__all__ = ["MiscMethods"]


class MiscMethods:
    def __init__(self, rest: RestTransport) -> None:
        self._rest = rest

    async def user_geo(self) -> str | None:
        """Код страны, который площадка определила по адресу."""
        payload = await self._rest.get(Service.PUBLIC, "/user-geo")
        if not isinstance(payload, dict):
            raise PlayerokError("Неожиданный ответ /user-geo")
        country = payload.get("country")
        return str(country) if country else None

    async def promo_banners(self) -> list[dict[str, Any]]:
        """Промо-баннеры главной."""
        payload = await self._rest.get(Service.BFF, "/promo-banners")
        items = payload.get("items") if isinstance(payload, dict) else None
        return list(items) if isinstance(items, list) else []

    async def quick_deal_widgets(
        self,
        *,
        category_id: str | None = None,
        on_main: bool | None = None,
    ) -> Any:
        """Виджеты быстрой покупки. Нужен либо категория, либо показ на главной."""
        if category_id is None and on_main is None:
            raise ValueError("Укажите category_id или on_main")
        return await self._rest.get(
            Service.PUBLIC,
            "/quick-deal-widgets",
            params=drop_none({"categoryId": category_id, "onMain": on_main}),
        )

    async def session_warning(self) -> Any:
        """Предупреждение о подозрительной сессии, если оно есть."""
        return await self._rest.get(Service.PUBLIC, "/auth/session-warning", auth=True)

    async def publish_block_reason(self) -> Any:
        """Почему аккаунту запрещено публиковать товары."""
        return await self._rest.get(Service.PUBLIC, "/user/publish-block-reason", auth=True)

    async def send_funds_protection_code(
        self,
        code_type: FundsProtectionCodeType | str,
    ) -> Any:
        """Выслать на почту код защиты средств."""
        return await self._rest.post(
            Service.PUBLIC,
            "/funds-protection/send-email-code",
            form={"type": str(code_type)},
            auth=True,
        )

    async def feature_flags(self, keys: list[str]) -> dict[str, Any]:
        """Прочитать feature-флаги площадки."""
        return await self._rest.feature_flags(keys)

    async def websocket_url(self) -> str | None:
        """Актуальный адрес подписок из флага `ws-url`.

        Площадка может переехать на другой хост, не меняя фронт, —
        слушатель спрашивает адрес здесь, а не держит его в коде.
        """
        attachment = await self._rest.flag_value("ws-url")
        if isinstance(attachment, dict):
            url = attachment.get("url")
            return str(url) if url else None
        return None
