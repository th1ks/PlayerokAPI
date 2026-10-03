"""Сделки покупателя и продавца."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..enums import MessageTemplateType
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport, RestTransport
from ..types import Deal, MessageTemplate, Page, Transaction
from . import fields

__all__ = ["DealsMethods"]

_FIELDS = fields.DEAL
_PAGE_INFO = fields.PAGE_INFO
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
_PROBLEM_TYPES = f"""
query MessageTemplates($pagination: Pagination, $filter: MessageTemplateFilter!) {{
    messageTemplates(pagination: $pagination, filter: $filter) {{
        edges {{ node {{ id title text type groupId sequence }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_REPORT_PROBLEM = f"""
mutation ReportDealProblem($input: ReportDealProblemInput!) {{
    reportDealProblem(input: $input) {{ {_FIELDS} }}
}}
"""
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
        extra: Mapping[str, Any] | None = None,
    ) -> Transaction:
        """Купить товар через REST. Запрос отправляется один раз без автоповтора."""
        if not item_id or not transaction_provider_id:
            raise ValueError("Нужны item_id и transaction_provider_id")
        body = dict(extra or {})
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

    async def problem_types(self, *, finished: bool = False) -> list[MessageTemplate]:
        """Варианты проблемы для жалобы по сделке.

        Площадка хранит их как шаблоны сообщений: активная сделка и
        завершённая разведены по разным типам.
        """
        template_type = (
            MessageTemplateType.FINISHED_DEAL_PROBLEM
            if finished
            else MessageTemplateType.ACTIVE_DEAL_PROBLEM
        )
        data = await self._graphql.execute(
            _PROBLEM_TYPES,
            {"pagination": {"first": 100}, "filter": {"type": template_type.value}},
            operation_name="MessageTemplates",
            auth=True,
        )
        page: Page[MessageTemplate] = Page.from_connection(
            _object(data, "messageTemplates"), MessageTemplate
        )
        return page.items

    async def report_problem(self, deal_id: str, problem_type_id: str, description: str) -> Deal:
        """Пожаловаться на проблему по сделке.

        `problem_type_id` — идентификатор из `problem_types()`.
        """
        if not problem_type_id or not description:
            raise ValueError("Нужны problem_type_id и description")
        data = await self._graphql.execute(
            _REPORT_PROBLEM,
            {
                "input": {
                    "dealId": deal_id,
                    "problemTypeId": problem_type_id,
                    "description": description,
                }
            },
            operation_name="ReportDealProblem",
            auth=True,
        )
        return Deal.from_dict(_object(data, "reportDealProblem"))

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
