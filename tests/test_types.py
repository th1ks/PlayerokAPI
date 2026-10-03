from __future__ import annotations

from datetime import datetime, timezone

from PlayerokAPI.enums import ChatType, ItemDealDirection, ItemStatus, UserRole
from PlayerokAPI.types import Chat, ChatMessage, Deal, Item, ItemProfile, Page, User


def test_unknown_enum_value_survives() -> None:
    status = ItemStatus("PENDING_SOMETHING_NEW")
    assert status.value == "PENDING_SOMETHING_NEW"
    assert status.is_known is False
    assert ItemStatus.APPROVED.is_known is True


def test_user_from_dict() -> None:
    user = User.from_dict(
        {
            "id": "u1",
            "username": "seller",
            "email": "a@b.c",
            "role": "USER",
            "createdAt": "2024-01-02T03:04:05Z",
            "unreadChatsCounter": 3,
            "balance": {"id": "b1", "value": 100.5, "available": 90.0, "frozen": 10.5},
            "profile": {"id": "u1", "username": "seller", "rating": 4.9, "avatarURL": "u"},
        }
    )
    assert user.role is UserRole.USER
    assert user.balance is not None and user.balance.available == 90.0
    assert user.rating == 4.9
    assert user.avatar_url == "u"
    assert user.created_at == datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_item_from_dict_keeps_raw() -> None:
    item = Item.from_dict(
        {
            "__typename": "MyItem",
            "id": "i1",
            "slug": "cool-account",
            "name": "Аккаунт",
            "price": 1500,
            "rawPrice": 1350,
            "status": "APPROVED",
            "game": {"id": "g1", "slug": "cs2", "name": "CS2", "type": "GAME"},
            "attachments": [{"id": "f1", "url": "https://i/1.png"}],
            "привет": "мир",
        }
    )
    assert item.is_mine is True
    assert item.url == "https://playerok.com/products/cool-account"
    assert item.status is ItemStatus.APPROVED
    assert item.game is not None and item.game.slug == "cs2"
    assert len(item.attachments) == 1
    assert item.raw["привет"] == "мир"


def test_missing_fields_do_not_break_parsing() -> None:
    item = ItemProfile.from_dict({"id": "i2"})
    assert item.price == 0.0
    assert item.game is None
    assert item.status is None


def test_page_from_connection() -> None:
    page: Page[ItemProfile] = Page.from_connection(
        {
            "edges": [
                {"cursor": "c1", "node": {"id": "i1"}},
                {"cursor": "c2", "node": {"id": "i2"}},
                {"cursor": "c3"},
            ],
            "pageInfo": {"hasNextPage": True, "endCursor": "c2"},
            "totalCount": 17,
        },
        ItemProfile,
    )
    assert len(page) == 2
    assert page.total_count == 17
    assert page.has_next_page is True
    assert page.end_cursor == "c2"
    assert [item.id for item in page] == ["i1", "i2"]


def test_chat_message_inherits_chat_id() -> None:
    chat = Chat.from_dict(
        {
            "id": "ch1",
            "type": "PM",
            "unreadMessagesCounter": 2,
            "participants": [{"id": "u1"}, {"id": "u2"}],
            "lastMessage": {"id": "m1", "text": "привет", "user": {"id": "u2"}},
        }
    )
    assert chat.type is ChatType.PM
    assert chat.last_message is not None
    assert chat.last_message.chat_id == "ch1"
    assert chat.last_message.is_system is False
    companion = chat.companion("u1")
    assert companion is not None and companion.id == "u2"


def test_message_chat_id_from_deal() -> None:
    message = ChatMessage.from_dict({"id": "m2", "deal": {"id": "d1", "chat": {"id": "ch9"}}})
    assert message.chat_id == "ch9"


def test_system_message() -> None:
    message = ChatMessage.from_dict({"id": "m3", "event": "CHAT_STARTED"})
    assert message.is_system is True
    assert message.author_id is None


def test_deal_direction() -> None:
    deal = Deal.from_dict({"id": "d1", "direction": "IN", "status": "PAID"})
    assert deal.direction is ItemDealDirection.IN
    assert deal.is_purchase is True
    assert deal.url == "https://playerok.com/deal/d1"
