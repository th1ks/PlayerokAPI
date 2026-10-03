"""Типы событий и их полезная нагрузка."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..types import Chat, ChatMessage, Deal, Item, Transaction, UserBalance

__all__ = [
    "BalanceUpdatedEvent",
    "ChatEvent",
    "DealEvent",
    "Event",
    "EventType",
    "ItemEvent",
    "MessageEvent",
    "TransactionEvent",
]


class EventType(str, Enum):
    NEW_MESSAGE = "NEW_MESSAGE"
    MESSAGE_EDITED = "MESSAGE_EDITED"
    MESSAGE_DELETED = "MESSAGE_DELETED"
    NEW_CHAT = "NEW_CHAT"
    CHAT_UPDATED = "CHAT_UPDATED"
    CHAT_READ = "CHAT_READ"
    NEW_DEAL = "NEW_DEAL"
    DEAL_UPDATED = "DEAL_UPDATED"
    ITEM_CREATED = "ITEM_CREATED"
    ITEM_UPDATED = "ITEM_UPDATED"
    ITEM_REMOVED = "ITEM_REMOVED"
    NEW_TRANSACTION = "NEW_TRANSACTION"
    BALANCE_UPDATED = "BALANCE_UPDATED"

    def __str__(self) -> str:
        return self.value


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Event:
    """Базовое событие. `raw` — то, что пришло от сервера."""

    type: EventType
    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    received_at: datetime = field(default_factory=_now)


@dataclass
class MessageEvent(Event):
    message: ChatMessage | None = None

    @property
    def chat_id(self) -> str | None:
        return self.message.chat_id if self.message else None

    @property
    def text(self) -> str | None:
        return self.message.text if self.message else None


@dataclass
class ChatEvent(Event):
    chat: Chat | None = None


@dataclass
class DealEvent(Event):
    deal: Deal | None = None


@dataclass
class ItemEvent(Event):
    item: Item | None = None


@dataclass
class TransactionEvent(Event):
    transaction: Transaction | None = None


@dataclass
class BalanceUpdatedEvent(Event):
    balance: UserBalance | None = None
