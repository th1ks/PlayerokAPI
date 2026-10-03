"""История кошелька и запросы на вывод средств."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport
from ..types import Page, Transaction

__all__ = ["TransactionsMethods"]

_FIELDS = """
    id operation direction providerId status statusDescription
    statusExpirationDate value fee createdAt completedAt isSuspicious
    user { id username avatarURL }
"""
_PAGE_INFO = "startCursor endCursor hasNextPage hasPreviousPage"
_SEARCH = f"""
query Transactions($pagination: Pagination, $filter: TransactionFilter!, $sort: Sort) {{
    transactions(pagination: $pagination, filter: $filter, sort: $sort) {{
        edges {{ node {{ {_FIELDS} }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_GET = f"query Transaction($id: UUID!) {{ transaction(id: $id) {{ {_FIELDS} }} }}"
_WITHDRAW = f"""
mutation RequestWithdrawal($input: CreateWithdrawalTransactionInput!) {{
    requestWithdrawal(input: $input) {{ {_FIELDS} }}
}}
"""


class TransactionsMethods:
    def __init__(self, graphql: GraphQLTransport) -> None:
        self._graphql = graphql

    async def search(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        sort: Mapping[str, Any] | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Page[Transaction]:
        """История транзакций с фильтром `TransactionFilter`."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _SEARCH,
            {
                "filter": dict(filter or {}),
                "sort": dict(sort) if sort else None,
                "pagination": drop_none({"first": first, "after": after}),
            },
            operation_name="Transactions",
            auth=True,
        )
        return Page.from_connection(_object(data, "transactions"), Transaction)

    async def get(self, transaction_id: str) -> Transaction:
        """Получить транзакцию по идентификатору."""
        data = await self._graphql.execute(
            _GET, {"id": transaction_id}, operation_name="Transaction", auth=True
        )
        return Transaction.from_dict(_object(data, "transaction"))

    async def withdraw(
        self,
        value: float,
        provider: str,
        account: str,
        *,
        confirmation_code: str | None = None,
        fields: Mapping[str, Any] | None = None,
    ) -> Transaction:
        """Запросить вывод; дополнительные поля — `CreateWithdrawalTransactionInput`."""
        if value <= 0:
            raise ValueError("value должен быть положительным")
        if not provider or not account:
            raise ValueError("Нужны provider и account")
        body = dict(fields or {})
        body.update(
            drop_none(
                {
                    "value": value,
                    "provider": provider,
                    "account": account,
                    "confirmationCode": confirmation_code,
                }
            )
        )
        data = await self._graphql.execute(
            _WITHDRAW, {"input": body}, operation_name="RequestWithdrawal", auth=True
        )
        return Transaction.from_dict(_object(data, "requestWithdrawal"))


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
