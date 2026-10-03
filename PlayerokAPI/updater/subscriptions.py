"""Документы подписок и разбор их полезной нагрузки в события."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..methods import fields
from ..types import Chat, ChatMessage, Deal, Item, Transaction, UserBalance
from .events import (
    BalanceUpdatedEvent,
    ChatEvent,
    DealEvent,
    Event,
    EventType,
    ItemEvent,
    MessageEvent,
    TransactionEvent,
)

__all__ = ["SUBSCRIPTIONS", "Subscription"]


@dataclass(frozen=True)
class Subscription:
    """Одна подписка: что спросить у сервера и во что превратить ответ."""

    event_type: EventType
    operation: str
    document: str
    root: str
    build: Callable[[EventType, dict[str, Any]], Event]
    #: Переменные, которые сервер требует непустыми.
    required_variables: tuple[str, ...] = ()


def _message(event_type: EventType, payload: dict[str, Any]) -> Event:
    return MessageEvent(type=event_type, raw=payload, message=ChatMessage.from_dict(payload))


def _chat(event_type: EventType, payload: dict[str, Any]) -> Event:
    return ChatEvent(type=event_type, raw=payload, chat=Chat.from_dict(payload))


def _deal(event_type: EventType, payload: dict[str, Any]) -> Event:
    return DealEvent(type=event_type, raw=payload, deal=Deal.from_dict(payload))


def _item(event_type: EventType, payload: dict[str, Any]) -> Event:
    return ItemEvent(type=event_type, raw=payload, item=Item.from_dict(payload))


def _transaction(event_type: EventType, payload: dict[str, Any]) -> Event:
    return TransactionEvent(
        type=event_type, raw=payload, transaction=Transaction.from_dict(payload)
    )


def _balance(event_type: EventType, payload: dict[str, Any]) -> Event:
    return BalanceUpdatedEvent(type=event_type, raw=payload, balance=UserBalance.from_dict(payload))


def _doc(operation: str, signature: str, root_call: str, body: str) -> str:
    return f"subscription {operation}{signature} {{\n    {root_call} {{ {body} }}\n}}"


SUBSCRIPTIONS: tuple[Subscription, ...] = (
    Subscription(
        EventType.NEW_MESSAGE,
        "chatMessageCreated",
        _doc(
            "chatMessageCreated",
            "($filter: ChatMessageWSFilter!)",
            "chatMessageCreated(filter: $filter)",
            fields.MESSAGE,
        ),
        "chatMessageCreated",
        _message,
        ("filter",),
    ),
    Subscription(
        EventType.MESSAGE_EDITED,
        "chatMessageUpdated",
        _doc(
            "chatMessageUpdated",
            "($filter: ChatMessageWSFilter!)",
            "chatMessageUpdated(filter: $filter)",
            fields.MESSAGE,
        ),
        "chatMessageUpdated",
        _message,
        ("filter",),
    ),
    Subscription(
        EventType.MESSAGE_DELETED,
        "chatMessageRemoved",
        _doc(
            "chatMessageRemoved",
            "($filter: ChatMessageWSFilter!)",
            "chatMessageRemoved(filter: $filter)",
            fields.MESSAGE,
        ),
        "chatMessageRemoved",
        _message,
        ("filter",),
    ),
    Subscription(
        EventType.NEW_CHAT,
        "chatCreated",
        _doc("chatCreated", "($filter: ChatFilter)", "chatCreated(filter: $filter)", fields.CHAT),
        "chatCreated",
        _chat,
    ),
    Subscription(
        EventType.CHAT_UPDATED,
        "chatUpdated",
        _doc("chatUpdated", "($filter: ChatFilter)", "chatUpdated(filter: $filter)", fields.CHAT),
        "chatUpdated",
        _chat,
    ),
    Subscription(
        EventType.CHAT_READ,
        "chatMarkedAsRead",
        _doc(
            "chatMarkedAsRead",
            "($filter: ChatFilter)",
            "chatMarkedAsRead(filter: $filter)",
            fields.CHAT,
        ),
        "chatMarkedAsRead",
        _chat,
    ),
    Subscription(
        EventType.NEW_DEAL,
        "dealCreated",
        _doc(
            "dealCreated", "($filter: ItemDealFilter!)", "dealCreated(filter: $filter)", fields.DEAL
        ),
        "dealCreated",
        _deal,
        ("filter",),
    ),
    Subscription(
        EventType.DEAL_UPDATED,
        "dealUpdated",
        _doc(
            "dealUpdated", "($filter: ItemDealFilter!)", "dealUpdated(filter: $filter)", fields.DEAL
        ),
        "dealUpdated",
        _deal,
        ("filter",),
    ),
    Subscription(
        EventType.ITEM_CREATED,
        "itemCreated",
        _doc("itemCreated", "($filter: ItemFilter!)", "itemCreated(filter: $filter)", fields.ITEM),
        "itemCreated",
        _item,
        ("filter",),
    ),
    Subscription(
        EventType.ITEM_UPDATED,
        "itemUpdated",
        _doc("itemUpdated", "($filter: ItemFilter!)", "itemUpdated(filter: $filter)", fields.ITEM),
        "itemUpdated",
        _item,
        ("filter",),
    ),
    Subscription(
        EventType.ITEM_REMOVED,
        "itemRemoved",
        _doc("itemRemoved", "($filter: ItemFilter!)", "itemRemoved(filter: $filter)", fields.ITEM),
        "itemRemoved",
        _item,
        ("filter",),
    ),
    Subscription(
        EventType.NEW_TRANSACTION,
        "transactionCreated",
        _doc(
            "transactionCreated",
            "($filter: TransactionFilter!)",
            "transactionCreated(filter: $filter)",
            fields.TRANSACTION,
        ),
        "transactionCreated",
        _transaction,
        ("filter",),
    ),
    Subscription(
        EventType.BALANCE_UPDATED,
        "userBalanceUpdated",
        _doc(
            "userBalanceUpdated",
            "",
            "userBalanceUpdated",
            "id value available frozen pendingIncome withdrawable totalWithdrawable",
        ),
        "userBalanceUpdated",
        _balance,
    ),
)


def by_type(event_types: Mapping[EventType, Any] | None = None) -> tuple[Subscription, ...]:
    """Подписки для перечисленных типов событий."""
    if event_types is None:
        return SUBSCRIPTIONS
    return tuple(sub for sub in SUBSCRIPTIONS if sub.event_type in event_types)
