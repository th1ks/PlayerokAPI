"""Сделки покупателя и продавца."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport, RestTransport
from ..types import Deal, Page, Transaction

__all__ = ["DealsMethods"]

_FIELDS = """
    id status prevStatus statusDescription direction hasProblem obtaining
    commentFromBuyer isAutomated createdAt completedAt statusExpirationDate
    item { __typename id name price }
    user { id username avatarURL }
    completedBy { id username }
    chat { id }
    transaction { id value fee status operation providerId createdAt }
    testimonial { id rating text status }
"""
_PAGE_INFO = "startCursor endCursor hasNextPage hasPreviousPage"
_SEARCH = f"""
query Deals($pagination: Pagination, $filter: ItemDealFilter!, $sort: Sort) {{
    deals(pagination: $pagination, filter: $filter, sort: $sort) {{
        edges {{ node {{ {_FIELDS} }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_GET = f"query Deal($id: UUID!) {{ deal(id: $id) {{ {_FIELDS} }} }}"
_UPDATE = f"""
mutation UpdateDeal($input: UpdateItemDealInput!) {{
    updateDeal(input: $input) {{ {_FIELDS} }}
}}
"""


class DealsMethods:
    def __init__(self, graphql: GraphQLTransport, rest: RestTransport) -> None:
        self._graphql = graphql
        self._rest = rest

    async def search(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        sort: Mapping[str, Any] | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Page[Deal]:
        """Список сделок с фильтром `ItemDealFilter` и курсорной пагинацией."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _SEARCH,
            {
                "filter": dict(filter or {}),
                "sort": dict(sort) if sort else None,
                "pagination": drop_none({"first": first, "after": after}),
            },
            operation_name="Deals",
            auth=True,
        )
        return Page.from_connection(_object(data, "deals"), Deal)

    async def get(self, deal_id: str) -> Deal:
        """Получить сделку по идентификатору."""
        data = await self._graphql.execute(_GET, {"id": deal_id}, operation_name="Deal", auth=True)
        return Deal.from_dict(_object(data, "deal"))

    async def create(
        self,
        item_id: str,
        transaction_provider_id: str,
        *,
        comment_from_buyer: str | None = None,
        confirmation_code: str | None = None,
        fields: Mapping[str, Any] | None = None,
    ) -> Transaction:
        """Купить товар через REST. Запрос отправляется один раз без автоповтора."""
        if not item_id or not transaction_provider_id:
            raise ValueError("Нужны item_id и transaction_provider_id")
        body = dict(fields or {})
        body.update(
            drop_none(
                {
                    "itemId": item_id,
                    "transactionProviderId": transaction_provider_id,
                    "commentFromBuyer": comment_from_buyer,
                    "confirmationCode": confirmation_code,
                }
            )
        )
        payload = await self._rest.post(
            Service.PUBLIC,
            "/deals/create",
            form=body,
            auth=True,
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("transaction"), dict):
            raise PlayerokError("Сервер не вернул транзакцию созданной сделки")
        return Transaction.from_dict(payload["transaction"])

    async def update(self, deal_id: str, changes: Mapping[str, Any]) -> Deal:
        """Изменить сделку; ключи changes соответствуют `UpdateItemDealInput`."""
        if not changes:
            raise ValueError("Передайте изменения сделки")
        body = dict(changes)
        body["id"] = deal_id
        data = await self._graphql.execute(
            _UPDATE, {"input": body}, operation_name="UpdateDeal", auth=True
        )
        return Deal.from_dict(_object(data, "updateDeal"))


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
