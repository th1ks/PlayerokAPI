"""Пополнение баланса: провайдеры, способы оплаты и карты."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..common.utils import drop_none
from ..enums import (
    PaymentCurrency,
    TransactionDirection,
    TransactionForm,
    TransactionOperation,
    TransactionProvider,
)
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport
from ..types import BankCard, PaymentMethod, PaymentProvider
from . import fields

__all__ = ["PaymentsMethods"]

_LIMITS = "limits { incoming { min max } outgoing { min max } }"
_METHOD = f"id name providerId enabled fee {_LIMITS}"
_PROVIDER = f"""
    id name description fee minFeeAmount currency {_LIMITS}
    paymentMethods {{ {_METHOD} }}
"""
_CARD = "id cardFirstSix cardLastFour cardType status isChosen userId"

_PROVIDERS = f"""
query TransactionProviders($filter: TransactionProviderFilter!) {{
    transactionProviders(filter: $filter) {{ {_PROVIDER} }}
}}
"""
_METHODS = f"""
query TransactionPaymentMethods($filter: TransactionPaymentMethodFilter!) {{
    transactionPaymentMethods(filter: $filter) {{ {_METHOD} }}
}}
"""
_CARDS = f"""
query VerifiedCards($filter: CardFilter, $pagination: Pagination) {{
    verifiedCards(filter: $filter, pagination: $pagination) {{
        edges {{ node {{ {_CARD} }} }}
        pageInfo {{ {fields.PAGE_INFO} }}
        totalCount
    }}
}}
"""
_CREATE_URL = """
mutation CreatePaymentURL($input: CreateDepositTransactionInput!) {
    createPaymentURL(input: $input)
}
"""
_SET_CHOSEN = """
mutation SetChosenCard($input: SetChosenCardInput!) { setChosenCard(input: $input) }
"""
_DELETE_CARD = """
mutation DeleteCard($input: DeleteCardInput!) { deleteCard(input: $input) }
"""
_VERIFY_CARD = """
mutation VerifyCard($input: VerifyCardInput!) {
    verifyCard(input: $input) { redirectUrl }
}
"""


class PaymentsMethods:
    """Пополнение кошелька и привязанные карты.

    `create_payment_url` возвращает адрес платёжной страницы провайдера —
    дальше пользователь платит в браузере, а результат придёт событием
    `NEW_TRANSACTION`.
    """

    def __init__(self, graphql: GraphQLTransport) -> None:
        self._graphql = graphql

    async def providers(
        self,
        *,
        direction: TransactionDirection | str = TransactionDirection.IN,
        form: TransactionForm | str | None = None,
    ) -> list[PaymentProvider]:
        """Провайдеры для пополнения (`IN`) или вывода (`OUT`)."""
        filters = drop_none({"direction": str(direction), "transactionForm": _opt(form)})
        data = await self._graphql.execute(
            _PROVIDERS,
            {"filter": filters},
            operation_name="TransactionProviders",
            auth=True,
        )
        return [PaymentProvider.from_dict(item) for item in _items(data, "transactionProviders")]

    async def payment_methods(
        self,
        provider: TransactionProvider | str,
        *,
        direction: TransactionDirection | str | None = None,
    ) -> list[PaymentMethod]:
        """Способы оплаты внутри провайдера."""
        filters = drop_none({"providerId": str(provider), "direction": _opt(direction)})
        data = await self._graphql.execute(
            _METHODS,
            {"filter": filters},
            operation_name="TransactionPaymentMethods",
            auth=True,
        )
        return [PaymentMethod.from_dict(item) for item in _items(data, "transactionPaymentMethods")]

    async def create_payment_url(
        self,
        value: float,
        provider: TransactionProvider | str,
        *,
        payment_method: str | None = None,
        currency: PaymentCurrency | str | None = None,
        operation: TransactionOperation | str | None = None,
        promocode: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        account: str | None = None,
        sbp_bank_member_id: str | None = None,
        confirmation_code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> str:
        """Создать платёж и получить адрес платёжной страницы.

        Остальные поля `CreateDepositTransactionInput` передаются через `extra`.
        """
        if value <= 0:
            raise ValueError("value должен быть положительным")

        provider_data = drop_none(
            {"paymentMethodId": payment_method, "sbpBankMemberId": sbp_bank_member_id}
        )
        user_data = drop_none({"email": email, "phoneNumber": phone_number, "account": account})

        body: dict[str, Any] = dict(extra or {})
        body.update(
            drop_none(
                {
                    "value": value,
                    "provider": str(provider),
                    "currency": _opt(currency),
                    "operation": _opt(operation),
                    "promocode": promocode,
                    "confirmationCode": confirmation_code,
                    "providerData": provider_data or None,
                    "userData": user_data or None,
                }
            )
        )

        data = await self._graphql.execute(
            _CREATE_URL, {"input": body}, operation_name="CreatePaymentURL", auth=True
        )
        url = data.get("createPaymentURL")
        if not isinstance(url, str) or not url:
            raise PlayerokError("Сервер не вернул адрес оплаты")
        return url

    async def cards(self, *, user_id: str | None = None, first: int = 20) -> list[BankCard]:
        """Привязанные карты."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _CARDS,
            {
                "filter": drop_none({"userId": user_id}),
                "pagination": {"first": first},
            },
            operation_name="VerifiedCards",
            auth=True,
        )
        connection = data.get("verifiedCards")
        if not isinstance(connection, dict):
            raise PlayerokError("Пустой или неожиданный ответ verifiedCards")
        return [
            BankCard.from_dict(edge["node"])
            for edge in (connection.get("edges") or [])
            if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
        ]

    async def set_chosen_card(self, card_id: str) -> bool:
        """Сделать карту основной для выплат."""
        data = await self._graphql.execute(
            _SET_CHOSEN,
            {"input": {"cardId": card_id}},
            operation_name="SetChosenCard",
            auth=True,
        )
        return bool(data.get("setChosenCard"))

    async def delete_card(self, card_id: str) -> bool:
        """Отвязать карту."""
        data = await self._graphql.execute(
            _DELETE_CARD,
            {"input": {"cardId": card_id}},
            operation_name="DeleteCard",
            auth=True,
        )
        return bool(data.get("deleteCard"))

    async def verify_card(self, amount: float) -> str:
        """Начать проверку карты и получить адрес для подтверждения."""
        if amount <= 0:
            raise ValueError("amount должен быть положительным")
        data = await self._graphql.execute(
            _VERIFY_CARD,
            {"input": {"amount": amount}},
            operation_name="VerifyCard",
            auth=True,
        )
        response = data.get("verifyCard")
        if not isinstance(response, dict) or not response.get("redirectUrl"):
            raise PlayerokError("Сервер не вернул адрес подтверждения карты")
        return str(response["redirectUrl"])


def _opt(value: Any) -> str | None:
    return None if value is None else str(value)


def _items(data: dict[str, Any], key: str) -> Sequence[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return [item for item in value if isinstance(item, dict)]
