"""Модели данных Playerok.

Обычные dataclass-ы без внешних зависимостей. Каждая модель разбирается
методом `from_dict` и терпима к неполным ответам: GraphQL отдаёт ровно те
поля, которые запросили, поэтому всё, кроме идентификатора, опционально.
Исходный словарь остаётся в `raw` — туда можно залезть за полем, которое
библиотека ещё не знает.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from .common.utils import parse_datetime, to_float, to_int
from .enums import (
    ChatMessageButtonType,
    ChatMessageEvent,
    ChatStatus,
    ChatType,
    GameType,
    ItemDealDirection,
    ItemDealStatus,
    ItemPriority,
    ItemSellerType,
    ItemStatus,
    ItemStockType,
    TestimonialStatus,
    TransactionDirection,
    TransactionOperation,
    TransactionProvider,
    TransactionStatus,
    TransactionType,
    UserRole,
)

__all__ = [
    "Chat",
    "ChatMessage",
    "ChatMessageButton",
    "Deal",
    "DealProfile",
    "File",
    "Game",
    "GameCategory",
    "GameProfile",
    "Item",
    "ItemDataField",
    "ItemProfile",
    "ObtainingType",
    "Page",
    "Testimonial",
    "Transaction",
    "User",
    "UserBalance",
    "UserProfile",
]

T = TypeVar("T")


def _enum(cls: Any, value: Any) -> Any:
    return cls(value) if value is not None else None


def _list(cls: Any, values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    return [cls.from_dict(item) for item in values if isinstance(item, dict)]


# --- вспомогательные -----------------------------------------------------


@dataclass
class File:
    """Файл в хранилище площадки."""

    id: str
    url: str | None = None
    filename: str | None = None
    mime: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> File:
        return cls(
            id=data.get("id", ""),
            url=data.get("url"),
            filename=data.get("filename"),
            mime=data.get("mime"),
            raw=data,
        )


@dataclass
class Page(Generic[T]):
    """Страница курсорной выборки."""

    items: list[T] = field(default_factory=list)
    total_count: int = 0
    has_next_page: bool = False
    has_previous_page: bool = False
    start_cursor: str | None = None
    end_cursor: str | None = None

    def __iter__(self) -> Any:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    @classmethod
    def from_connection(cls, data: dict[str, Any] | None, node_type: Any) -> Page[Any]:
        data = data or {}
        info = data.get("pageInfo") or {}
        nodes = [
            node_type.from_dict(edge["node"])
            for edge in (data.get("edges") or [])
            if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
        ]
        return cls(
            items=nodes,
            total_count=to_int(data.get("totalCount"), 0) or 0,
            has_next_page=bool(info.get("hasNextPage")),
            has_previous_page=bool(info.get("hasPreviousPage")),
            start_cursor=info.get("startCursor"),
            end_cursor=info.get("endCursor"),
        )


# --- пользователи --------------------------------------------------------


@dataclass
class UserProfile:
    """Краткий профиль (`UserFragment`) — то, что видно в чатах и товарах."""

    id: str
    username: str | None = None
    avatar_url: str | None = None
    role: UserRole | None = None
    rating: float | None = None
    testimonial_counter: int | None = None
    is_online: bool | None = None
    is_blocked: bool = False
    is_vip: bool = False
    has_frozen_balance: bool = False
    support_chat_id: str | None = None
    system_chat_id: str | None = None
    created_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(
            id=data.get("id", ""),
            username=data.get("username"),
            avatar_url=data.get("avatarURL"),
            role=_enum(UserRole, data.get("role")),
            rating=to_float(data.get("rating")),
            testimonial_counter=to_int(data.get("testimonialCounter")),
            is_online=data.get("isOnline"),
            is_blocked=bool(data.get("isBlocked")),
            is_vip=bool(data.get("isVip")),
            has_frozen_balance=bool(data.get("hasFrozenBalance")),
            support_chat_id=data.get("supportChatId"),
            system_chat_id=data.get("systemChatId"),
            created_at=parse_datetime(data.get("createdAt")),
            raw=data,
        )


@dataclass
class UserBalance:
    """Кошелёк."""

    id: str | None = None
    value: float = 0.0
    available: float = 0.0
    frozen: float = 0.0
    pending_income: float = 0.0
    withdrawable: float = 0.0
    total_withdrawable: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserBalance:
        return cls(
            id=data.get("id"),
            value=to_float(data.get("value"), 0.0) or 0.0,
            available=to_float(data.get("available"), 0.0) or 0.0,
            frozen=to_float(data.get("frozen"), 0.0) or 0.0,
            pending_income=to_float(data.get("pendingIncome"), 0.0) or 0.0,
            withdrawable=to_float(data.get("withdrawable"), 0.0) or 0.0,
            total_withdrawable=to_float(data.get("totalWithdrawable"), 0.0) or 0.0,
            raw=data,
        )


@dataclass
class User:
    """Полный профиль — то, что отдаёт `viewer` про своего владельца."""

    id: str
    username: str | None = None
    email: str | None = None
    role: UserRole | None = None
    balance: UserBalance | None = None
    profile: UserProfile | None = None
    is_blocked: bool = False
    is_verified: bool = False
    is_vip: bool = False
    has_frozen_balance: bool = False
    has_confirmed_phone_number: bool = False
    can_publish_items: bool = False
    approved_seller: bool = False
    unread_chats_counter: int = 0
    testimonial_counter: int = 0
    support_chat_id: str | None = None
    system_chat_id: str | None = None
    created_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def avatar_url(self) -> str | None:
        return self.profile.avatar_url if self.profile else None

    @property
    def rating(self) -> float | None:
        return self.profile.rating if self.profile else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        profile = data.get("profile")
        balance = data.get("balance")
        return cls(
            id=data.get("id", ""),
            username=data.get("username"),
            email=data.get("email"),
            role=_enum(UserRole, data.get("role")),
            balance=UserBalance.from_dict(balance) if isinstance(balance, dict) else None,
            profile=UserProfile.from_dict(profile) if isinstance(profile, dict) else None,
            is_blocked=bool(data.get("isBlocked")),
            is_verified=bool(data.get("isVerified")),
            is_vip=bool(data.get("isVip")),
            has_frozen_balance=bool(data.get("hasFrozenBalance")),
            has_confirmed_phone_number=bool(data.get("hasConfirmedPhoneNumber")),
            can_publish_items=bool(data.get("canPublishItems")),
            approved_seller=bool(data.get("approvedSeller")),
            unread_chats_counter=to_int(data.get("unreadChatsCounter"), 0) or 0,
            testimonial_counter=to_int(data.get("testimonialCounter"), 0) or 0,
            support_chat_id=data.get("supportChatId"),
            system_chat_id=data.get("systemChatId"),
            created_at=parse_datetime(data.get("createdAt")),
            raw=data,
        )


# --- игры и категории ----------------------------------------------------


@dataclass
class GameProfile:
    id: str
    slug: str | None = None
    name: str | None = None
    type: GameType | None = None
    logo: File | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameProfile:
        logo = data.get("logo")
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug"),
            name=data.get("name"),
            type=_enum(GameType, data.get("type")),
            logo=File.from_dict(logo) if isinstance(logo, dict) else None,
            raw=data,
        )


@dataclass
class Game:
    id: str
    slug: str | None = None
    name: str | None = None
    type: GameType | None = None
    description: str | None = None
    logo: File | None = None
    banner: File | None = None
    logo_link: str | None = None
    banner_link: str | None = None
    items_counter: float = 0.0
    seller_fee: float | None = None
    tags: list[str] = field(default_factory=list)
    is_new: bool = False
    created_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Game:
        logo, banner = data.get("logo"), data.get("banner")
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug"),
            name=data.get("name"),
            type=_enum(GameType, data.get("type")),
            description=data.get("description"),
            logo=File.from_dict(logo) if isinstance(logo, dict) else None,
            banner=File.from_dict(banner) if isinstance(banner, dict) else None,
            logo_link=data.get("logoLink"),
            banner_link=data.get("bannerLink"),
            items_counter=to_float(data.get("itemsCounter"), 0.0) or 0.0,
            seller_fee=to_float(data.get("sellerFee")),
            tags=list(data.get("tags") or []),
            is_new=bool(data.get("isNew")),
            created_at=parse_datetime(data.get("createdAt")),
            raw=data,
        )


@dataclass
class ObtainingType:
    """Способ получения товара внутри категории."""

    id: str
    name: str | None = None
    description: str | None = None
    game_category_id: str | None = None
    fee_multiplier: float | None = None
    stock_type: ItemStockType | None = None
    instruction_for_buyer: str | None = None
    instruction_for_seller: str | None = None
    no_comment_from_buyer: bool = False
    sequence: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObtainingType:
        return cls(
            id=data.get("id", ""),
            name=data.get("name"),
            description=data.get("description"),
            game_category_id=data.get("gameCategoryId"),
            fee_multiplier=to_float(data.get("feeMultiplier")),
            stock_type=_enum(ItemStockType, data.get("stockType")),
            instruction_for_buyer=data.get("instructionForBuyer"),
            instruction_for_seller=data.get("instructionForSeller"),
            no_comment_from_buyer=bool(data.get("noCommentFromBuyer")),
            sequence=to_int(data.get("sequence")),
            raw=data,
        )


@dataclass
class GameCategory:
    id: str
    slug: str | None = None
    name: str | None = None
    game_id: str | None = None
    category_id: str | None = None
    items_counter: float = 0.0
    fee_multiplier: float | None = None
    seller_fee: float | None = None
    obtaining: str | None = None
    stock_type: ItemStockType | None = None
    instruction_for_buyer: str | None = None
    instruction_for_seller: str | None = None
    auto_confirm_period: str | None = None
    options: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameCategory:
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug"),
            name=data.get("name"),
            game_id=data.get("gameId"),
            category_id=data.get("categoryId"),
            items_counter=to_float(data.get("itemsCounter"), 0.0) or 0.0,
            fee_multiplier=to_float(data.get("feeMultiplier")),
            seller_fee=to_float(data.get("sellerFee")),
            obtaining=data.get("obtaining"),
            stock_type=_enum(ItemStockType, data.get("stockType")),
            instruction_for_buyer=data.get("instructionForBuyer"),
            instruction_for_seller=data.get("instructionForSeller"),
            auto_confirm_period=data.get("autoConfirmPeriod"),
            options=list(data.get("options") or []),
            raw=data,
        )


# --- товары --------------------------------------------------------------


@dataclass
class ItemDataField:
    """Поле данных товара или способа получения."""

    id: str
    label: str | None = None
    value: str | None = None
    type: str | None = None
    input_type: str | None = None
    required: bool = False
    hidden: bool = False
    copyable: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ItemDataField:
        return cls(
            id=data.get("id", ""),
            label=data.get("label"),
            value=data.get("value"),
            type=data.get("type"),
            input_type=data.get("inputType"),
            required=bool(data.get("required")),
            hidden=bool(data.get("hidden")),
            copyable=bool(data.get("copyable")),
            raw=data,
        )


@dataclass
class ItemProfile:
    """Товар в списке — то, что приходит из `items`."""

    id: str
    slug: str | None = None
    name: str | None = None
    price: float = 0.0
    raw_price: float = 0.0
    status: ItemStatus | None = None
    priority: ItemPriority | None = None
    seller_type: ItemSellerType | None = None
    fee_multiplier: float | None = None
    game: GameProfile | None = None
    category: GameCategory | None = None
    user: UserProfile | None = None
    attachment: File | None = None
    obtaining: str | None = None
    obtaining_type: ObtainingType | None = None
    views_counter: int | None = None
    deals_counter: int | None = None
    priority_position: int | None = None
    sequence: int | None = None
    is_automated: bool = False
    keep_in_sale: bool | None = None
    created_at: datetime | None = None
    approval_date: datetime | None = None
    deleted_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def url(self) -> str:
        return f"https://playerok.com/products/{self.slug or self.id}"

    @property
    def is_mine(self) -> bool:
        """True, если сервер отдал реализацию `MyItemProfile`."""
        return str(self.raw.get("__typename", "")).startswith("My")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ItemProfile:
        return cls(**_item_profile_fields(data), raw=data)


@dataclass
class Item:
    """Товар целиком — то, что приходит из `item`."""

    id: str
    slug: str | None = None
    name: str | None = None
    description: str | None = None
    comment: str | None = None
    price: float = 0.0
    raw_price: float = 0.0
    status: ItemStatus | None = None
    status_description: str | None = None
    priority: ItemPriority | None = None
    seller_type: ItemSellerType | None = None
    fee_multiplier: float | None = None
    game: GameProfile | None = None
    category: GameCategory | None = None
    user: UserProfile | None = None
    buyer: UserProfile | None = None
    attachments: list[File] = field(default_factory=list)
    attachment_links: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    data_fields: list[ItemDataField] = field(default_factory=list)
    obtaining_type: ObtainingType | None = None
    views_counter: int | None = None
    deals_counter: int | None = None
    priority_position: int | None = None
    sequence: int | None = None
    editable: bool = False
    keep_in_sale: bool = False
    is_automated: bool = False
    may_be_published: bool | None = None
    republish_available: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approval_date: datetime | None = None
    deleted_at: datetime | None = None
    status_expiration_date: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def url(self) -> str:
        return f"https://playerok.com/products/{self.slug or self.id}"

    @property
    def is_mine(self) -> bool:
        return str(self.raw.get("__typename", "")).startswith("My")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Item:
        game, category = data.get("game"), data.get("category")
        user, buyer = data.get("user"), data.get("buyer")
        obtaining = data.get("obtainingType")
        return cls(
            id=data.get("id", ""),
            slug=data.get("slug"),
            name=data.get("name"),
            description=data.get("description"),
            comment=data.get("comment"),
            price=to_float(data.get("price"), 0.0) or 0.0,
            raw_price=to_float(data.get("rawPrice"), 0.0) or 0.0,
            status=_enum(ItemStatus, data.get("status")),
            status_description=data.get("statusDescription"),
            priority=_enum(ItemPriority, data.get("priority")),
            seller_type=_enum(ItemSellerType, data.get("sellerType")),
            fee_multiplier=to_float(data.get("feeMultiplier")),
            game=GameProfile.from_dict(game) if isinstance(game, dict) else None,
            category=GameCategory.from_dict(category) if isinstance(category, dict) else None,
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            buyer=UserProfile.from_dict(buyer) if isinstance(buyer, dict) else None,
            attachments=_list(File, data.get("attachments")),
            attachment_links=list(data.get("attachmentLinks") or []),
            attributes=dict(data.get("attributes") or {}),
            data_fields=_list(ItemDataField, data.get("dataFields")),
            obtaining_type=ObtainingType.from_dict(obtaining)
            if isinstance(obtaining, dict)
            else None,
            views_counter=to_int(data.get("viewsCounter")),
            deals_counter=to_int(data.get("dealsCounter")),
            priority_position=to_int(data.get("priorityPosition")),
            sequence=to_int(data.get("sequence")),
            editable=bool(data.get("editable")),
            keep_in_sale=bool(data.get("keepInSale")),
            is_automated=bool(data.get("isAutomated")),
            may_be_published=data.get("mayBePublished"),
            republish_available=data.get("republishAvailable"),
            created_at=parse_datetime(data.get("createdAt")),
            updated_at=parse_datetime(data.get("updatedAt")),
            approval_date=parse_datetime(data.get("approvalDate")),
            deleted_at=parse_datetime(data.get("deletedAt")),
            status_expiration_date=parse_datetime(data.get("statusExpirationDate")),
            raw=data,
        )


def _item_profile_fields(data: dict[str, Any]) -> dict[str, Any]:
    game, category = data.get("game"), data.get("category")
    user, attachment = data.get("user"), data.get("attachment")
    obtaining = data.get("obtainingType")
    return {
        "id": data.get("id", ""),
        "slug": data.get("slug"),
        "name": data.get("name"),
        "price": to_float(data.get("price"), 0.0) or 0.0,
        "raw_price": to_float(data.get("rawPrice"), 0.0) or 0.0,
        "status": _enum(ItemStatus, data.get("status")),
        "priority": _enum(ItemPriority, data.get("priority")),
        "seller_type": _enum(ItemSellerType, data.get("sellerType")),
        "fee_multiplier": to_float(data.get("feeMultiplier")),
        "game": GameProfile.from_dict(game) if isinstance(game, dict) else None,
        "category": GameCategory.from_dict(category) if isinstance(category, dict) else None,
        "user": UserProfile.from_dict(user) if isinstance(user, dict) else None,
        "attachment": File.from_dict(attachment) if isinstance(attachment, dict) else None,
        "obtaining": data.get("obtaining"),
        "obtaining_type": ObtainingType.from_dict(obtaining)
        if isinstance(obtaining, dict)
        else None,
        "views_counter": to_int(data.get("viewsCounter")),
        "deals_counter": to_int(data.get("dealsCounter")),
        "priority_position": to_int(data.get("priorityPosition")),
        "sequence": to_int(data.get("sequence")),
        "is_automated": bool(data.get("isAutomated")),
        "keep_in_sale": data.get("keepInSale"),
        "created_at": parse_datetime(data.get("createdAt")),
        "approval_date": parse_datetime(data.get("approvalDate")),
        "deleted_at": parse_datetime(data.get("deletedAt")),
    }


# --- сделки и отзывы -----------------------------------------------------


@dataclass
class DealProfile:
    """Сделка в сокращённом виде — то, что висит на чате."""

    id: str
    status: ItemDealStatus | None = None
    status_description: str | None = None
    direction: ItemDealDirection | None = None
    has_problem: bool = False
    item: ItemProfile | None = None
    user: UserProfile | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    status_expiration_date: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DealProfile:
        item, user = data.get("item"), data.get("user")
        return cls(
            id=data.get("id", ""),
            status=_enum(ItemDealStatus, data.get("status")),
            status_description=data.get("statusDescription"),
            direction=_enum(ItemDealDirection, data.get("direction")),
            has_problem=bool(data.get("hasProblem")),
            item=ItemProfile.from_dict(item) if isinstance(item, dict) else None,
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            created_at=parse_datetime(data.get("createdAt")),
            updated_at=parse_datetime(data.get("updatedAt")),
            status_expiration_date=parse_datetime(data.get("statusExpirationDate")),
            raw=data,
        )


@dataclass
class Deal:
    """Сделка целиком."""

    id: str
    status: ItemDealStatus | None = None
    prev_status: ItemDealStatus | None = None
    status_description: str | None = None
    direction: ItemDealDirection | None = None
    has_problem: bool = False
    hassle_free: bool = False
    is_automated: bool = False
    problem_resolved_by_admin: bool = False
    comment_from_buyer: str | None = None
    obtaining: str | None = None
    obtaining_fields: list[ItemDataField] = field(default_factory=list)
    item: Item | None = None
    user: UserProfile | None = None
    completed_by: UserProfile | None = None
    chat_id: str | None = None
    transaction: Transaction | None = None
    testimonial: Testimonial | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    problem_reported_at: datetime | None = None
    status_expiration_date: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def url(self) -> str:
        return f"https://playerok.com/deal/{self.id}"

    @property
    def is_purchase(self) -> bool:
        return self.direction == ItemDealDirection.IN

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Deal:
        item, user = data.get("item"), data.get("user")
        chat, completed_by = data.get("chat"), data.get("completedBy")
        transaction, testimonial = data.get("transaction"), data.get("testimonial")
        return cls(
            id=data.get("id", ""),
            status=_enum(ItemDealStatus, data.get("status")),
            prev_status=_enum(ItemDealStatus, data.get("prevStatus")),
            status_description=data.get("statusDescription"),
            direction=_enum(ItemDealDirection, data.get("direction")),
            has_problem=bool(data.get("hasProblem")),
            hassle_free=bool(data.get("hassleFree")),
            is_automated=bool(data.get("isAutomated")),
            problem_resolved_by_admin=bool(data.get("problemResolvedByAdmin")),
            comment_from_buyer=data.get("commentFromBuyer"),
            obtaining=data.get("obtaining"),
            obtaining_fields=_list(ItemDataField, data.get("obtainingFields")),
            item=Item.from_dict(item) if isinstance(item, dict) else None,
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            completed_by=UserProfile.from_dict(completed_by)
            if isinstance(completed_by, dict)
            else None,
            chat_id=(chat or {}).get("id") if isinstance(chat, dict) else None,
            transaction=Transaction.from_dict(transaction)
            if isinstance(transaction, dict)
            else None,
            testimonial=Testimonial.from_dict(testimonial)
            if isinstance(testimonial, dict)
            else None,
            created_at=parse_datetime(data.get("createdAt")),
            updated_at=parse_datetime(data.get("updatedAt")),
            completed_at=parse_datetime(data.get("completedAt")),
            problem_reported_at=parse_datetime(data.get("problemReportedAt")),
            status_expiration_date=parse_datetime(data.get("statusExpirationDate")),
            raw=data,
        )


@dataclass
class Testimonial:
    """Отзыв о сделке."""

    id: str
    rating: float = 0.0
    text: str | None = None
    status: TestimonialStatus | None = None
    creator: UserProfile | None = None
    user: UserProfile | None = None
    deal: DealProfile | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Testimonial:
        creator, user, deal = data.get("creator"), data.get("user"), data.get("deal")
        return cls(
            id=data.get("id", ""),
            rating=to_float(data.get("rating"), 0.0) or 0.0,
            text=data.get("text"),
            status=_enum(TestimonialStatus, data.get("status")),
            creator=UserProfile.from_dict(creator) if isinstance(creator, dict) else None,
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            deal=DealProfile.from_dict(deal) if isinstance(deal, dict) else None,
            created_at=parse_datetime(data.get("createdAt")),
            updated_at=parse_datetime(data.get("updatedAt")),
            raw=data,
        )


# --- транзакции ----------------------------------------------------------


@dataclass
class Transaction:
    """Движение по кошельку."""

    id: str
    value: float = 0.0
    fee: float = 0.0
    status: TransactionStatus | None = None
    status_description: str | None = None
    direction: TransactionDirection | None = None
    operation: TransactionOperation | None = None
    type: TransactionType | None = None
    provider_id: TransactionProvider | None = None
    description: str | None = None
    invoice_id: str | None = None
    item_id: str | None = None
    user: UserProfile | None = None
    is_suspicious: bool = False
    is_suspended: bool = False
    created_at: datetime | None = None
    completed_at: datetime | None = None
    confirmed_at: datetime | None = None
    status_expiration_date: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def url(self) -> str:
        return f"https://playerok.com/transaction/{self.id}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transaction:
        user = data.get("user")
        return cls(
            id=data.get("id", ""),
            value=to_float(data.get("value"), 0.0) or 0.0,
            fee=to_float(data.get("fee"), 0.0) or 0.0,
            status=_enum(TransactionStatus, data.get("status")),
            status_description=data.get("statusDescription"),
            direction=_enum(TransactionDirection, data.get("direction")),
            operation=_enum(TransactionOperation, data.get("operation")),
            type=_enum(TransactionType, data.get("type")),
            provider_id=_enum(TransactionProvider, data.get("providerId")),
            description=data.get("description"),
            invoice_id=data.get("invoiceId"),
            item_id=data.get("itemId"),
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            is_suspicious=bool(data.get("isSuspicious")),
            is_suspended=bool(data.get("isSuspended")),
            created_at=parse_datetime(data.get("createdAt")),
            completed_at=parse_datetime(data.get("completedAt")),
            confirmed_at=parse_datetime(data.get("confirmedAt")),
            status_expiration_date=parse_datetime(data.get("statusExpirationDate")),
            raw=data,
        )


# --- чаты ----------------------------------------------------------------


@dataclass
class ChatMessageButton:
    text: str | None = None
    type: ChatMessageButtonType | None = None
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessageButton:
        return cls(
            text=data.get("text"),
            type=_enum(ChatMessageButtonType, data.get("type")),
            url=data.get("url"),
            raw=data,
        )


@dataclass
class ChatMessage:
    """Сообщение в чате.

    В схеме у сообщения нет поля с идентификатором чата, поэтому `chat_id`
    проставляет библиотека — из запроса или из фильтра подписки.
    """

    id: str
    text: str | None = None
    chat_id: str | None = None
    user: UserProfile | None = None
    event: ChatMessageEvent | None = None
    event_by_user: UserProfile | None = None
    event_to_user: UserProfile | None = None
    is_read: bool = False
    is_edited: bool = False
    is_suspicious: bool = False
    is_auto_response: bool = False
    is_bulk_messaging: bool = False
    reply_to_id: str | None = None
    images: list[File] = field(default_factory=list)
    image_links: list[str] = field(default_factory=list)
    file: File | None = None
    buttons: list[ChatMessageButton] = field(default_factory=list)
    deal: DealProfile | None = None
    item: ItemProfile | None = None
    transaction: Transaction | None = None
    pl_token_amount: int | None = None
    created_at: datetime | None = None
    deleted_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def is_system(self) -> bool:
        """Системное сообщение: событие площадки, а не текст от человека."""
        return self.event is not None or self.user is None

    @property
    def author_id(self) -> str | None:
        return self.user.id if self.user else None

    @classmethod
    def from_dict(cls, data: dict[str, Any], chat_id: str | None = None) -> ChatMessage:
        user = data.get("user")
        by_user, to_user = data.get("eventByUser"), data.get("eventToUser")
        deal, item = data.get("deal"), data.get("item")
        transaction, file = data.get("transaction"), data.get("file")
        if chat_id is None and isinstance(deal, dict):
            chat = deal.get("chat")
            chat_id = chat.get("id") if isinstance(chat, dict) else None
        return cls(
            id=data.get("id", ""),
            text=data.get("text"),
            chat_id=chat_id,
            user=UserProfile.from_dict(user) if isinstance(user, dict) else None,
            event=_enum(ChatMessageEvent, data.get("event")),
            event_by_user=UserProfile.from_dict(by_user) if isinstance(by_user, dict) else None,
            event_to_user=UserProfile.from_dict(to_user) if isinstance(to_user, dict) else None,
            is_read=bool(data.get("isRead")),
            is_edited=bool(data.get("isEdited")),
            is_suspicious=bool(data.get("isSuspicious")),
            is_auto_response=bool(data.get("isAutoResponse")),
            is_bulk_messaging=bool(data.get("isBulkMessaging")),
            reply_to_id=data.get("replyToId"),
            images=_list(File, data.get("images")),
            image_links=list(data.get("imageLinks") or []),
            file=File.from_dict(file) if isinstance(file, dict) else None,
            buttons=_list(ChatMessageButton, data.get("buttons")),
            deal=DealProfile.from_dict(deal) if isinstance(deal, dict) else None,
            item=ItemProfile.from_dict(item) if isinstance(item, dict) else None,
            transaction=Transaction.from_dict(transaction)
            if isinstance(transaction, dict)
            else None,
            pl_token_amount=to_int(data.get("plTokenAmount")),
            created_at=parse_datetime(data.get("createdAt")),
            deleted_at=parse_datetime(data.get("deletedAt")),
            raw=data,
        )


@dataclass
class Chat:
    """Диалог."""

    id: str
    type: ChatType | None = None
    status: ChatStatus | None = None
    unread_messages_counter: int = 0
    bookmarked: bool = False
    is_texting_allowed: bool = True
    has_frozen_balance: bool = False
    last_message: ChatMessage | None = None
    participants: list[UserProfile] = field(default_factory=list)
    owner: UserProfile | None = None
    agent: UserProfile | None = None
    active_deal: DealProfile | None = None
    deals: list[DealProfile] = field(default_factory=list)
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def url(self) -> str:
        return f"https://playerok.com/chats/{self.id}"

    def companion(self, my_id: str) -> UserProfile | None:
        """Собеседник в личном диалоге."""
        for participant in self.participants:
            if participant.id != my_id:
                return participant
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chat:
        chat_id = data.get("id", "")
        last = data.get("lastMessage")
        owner, agent = data.get("owner"), data.get("agent")
        active_deal = data.get("activeDeal")
        return cls(
            id=chat_id,
            type=_enum(ChatType, data.get("type")),
            status=_enum(ChatStatus, data.get("status")),
            unread_messages_counter=to_int(data.get("unreadMessagesCounter"), 0) or 0,
            bookmarked=bool(data.get("bookmarked")),
            is_texting_allowed=bool(data.get("isTextingAllowed", True)),
            has_frozen_balance=bool(data.get("hasFrozenBalance")),
            last_message=ChatMessage.from_dict(last, chat_id) if isinstance(last, dict) else None,
            participants=_list(UserProfile, data.get("participants")),
            owner=UserProfile.from_dict(owner) if isinstance(owner, dict) else None,
            agent=UserProfile.from_dict(agent) if isinstance(agent, dict) else None,
            active_deal=DealProfile.from_dict(active_deal)
            if isinstance(active_deal, dict)
            else None,
            deals=_list(DealProfile, data.get("deals")),
            created_at=parse_datetime(data.get("createdAt")),
            started_at=parse_datetime(data.get("startedAt")),
            finished_at=parse_datetime(data.get("finishedAt")),
            raw=data,
        )
