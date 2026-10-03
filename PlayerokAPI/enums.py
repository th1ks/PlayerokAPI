"""Перечисления из схемы Playerok.

Площадка добавляет значения без предупреждения, поэтому все перечисления
терпимы к незнакомому: `ItemStatus("НЕЧТО_НОВОЕ")` вернёт псевдо-член
с этим значением, а не упадёт с ValueError.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

__all__ = [
    "BankCardStatus",
    "BankCardType",
    "ChatAttachmentsSource",
    "ChatMessageButtonType",
    "ChatMessageEvent",
    "ChatStatus",
    "ChatType",
    "FeeMultiplier",
    "FundsProtectionCodeType",
    "GameCategoryDataFieldType",
    "GameType",
    "ItemBoosterType",
    "ItemDealDirection",
    "ItemDealStatus",
    "ItemPriority",
    "ItemSellerType",
    "ItemStatus",
    "ItemStockType",
    "MessageTemplateType",
    "NotificationProviderId",
    "PaymentCurrency",
    "PaymentGateway",
    "SortDirection",
    "TestimonialStatus",
    "TransactionDirection",
    "TransactionForm",
    "TransactionOperation",
    "TransactionPaymentMethod",
    "TransactionProvider",
    "TransactionStatus",
    "TransactionType",
    "UserRole",
]


class OpenEnum(str, Enum):
    """Строковое перечисление, не падающее на незнакомом значении."""

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if not isinstance(value, str):
            return None
        pseudo = str.__new__(cls, value)
        pseudo._name_ = value
        pseudo._value_ = value
        return pseudo

    @property
    def is_known(self) -> bool:
        """False, если значение пришло с сервера и его нет в схеме."""
        return self.name in type(self).__members__

    def __str__(self) -> str:
        return self.value


class ItemStatus(OpenEnum):
    DRAFT = "DRAFT"
    PENDING_MODERATION = "PENDING_MODERATION"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_STATUS_PAYMENT = "PENDING_STATUS_PAYMENT"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    SOLD = "SOLD"
    DISCONTINUED = "DISCONTINUED"
    REMOVED = "REMOVED"


class ItemPriority(OpenEnum):
    DEFAULT = "DEFAULT"
    PREMIUM = "PREMIUM"
    VIP = "VIP"
    CUSTOM = "CUSTOM"


class ItemSellerType(OpenEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class ItemStockType(OpenEnum):
    SINGLE = "SINGLE"
    MULTIPLE = "MULTIPLE"


class ItemBoosterType(OpenEnum):
    NONE = "NONE"
    PERIOD = "PERIOD"
    POSITION = "POSITION"
    VISUAL = "VISUAL"


class FeeMultiplier(OpenEnum):
    """Тариф комиссии продавца."""

    FIVE_PERCENT = "FIVE_PERCENT"
    TEN_PERCENT = "TEN_PERCENT"
    TWENTY_PERCENT = "TWENTY_PERCENT"


class ChatType(OpenEnum):
    PM = "PM"
    GROUP = "GROUP"
    SUPPORT = "SUPPORT"
    NOTIFICATIONS = "NOTIFICATIONS"


class ChatStatus(OpenEnum):
    NEW = "NEW"
    STARTED = "STARTED"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    FINISHED = "FINISHED"


class ChatMessageEvent(OpenEnum):
    CHAT_STARTED = "CHAT_STARTED"
    CHAT_FINISHED = "CHAT_FINISHED"
    CHAT_REASSIGNMENT = "CHAT_REASSIGNMENT"
    ASK_FOR_EXTERNAL_REVIEW = "ASK_FOR_EXTERNAL_REVIEW"
    INVITE_FRIEND = "INVITE_FRIEND"
    PHONE_VERIFICATION_COMPLETED = "PHONE_VERIFICATION_COMPLETED"
    PL_TOKEN_CREDITED = "PL_TOKEN_CREDITED"


class ChatMessageButtonType(OpenEnum):
    REDIRECT = "REDIRECT"
    CURRENT_BALANCE = "CURRENT_BALANCE"
    LOTTERY = "LOTTERY"
    LOTTERY_RESULTS = "LOTTERY_RESULTS"
    ASK_FOR_EXTERNAL_REVIEW = "ASK_FOR_EXTERNAL_REVIEW"


class ChatAttachmentsSource(OpenEnum):
    FILE_SERVICE = "FILE_SERVICE"
    LEGACY = "LEGACY"


class ItemDealStatus(OpenEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    SENT = "SENT"
    CONFIRMED = "CONFIRMED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class ItemDealDirection(OpenEnum):
    IN = "IN"
    """Покупка: деньги уходят со счёта."""

    OUT = "OUT"
    """Продажа: деньги приходят на счёт."""


class TestimonialStatus(OpenEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"


class TransactionStatus(OpenEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class TransactionDirection(OpenEnum):
    IN = "IN"
    OUT = "OUT"


class TransactionType(OpenEnum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class TransactionOperation(OpenEnum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    REFUND = "REFUND"
    REFERRAL_BONUS = "REFERRAL_BONUS"
    FRAGMENT_DEPOSIT = "FRAGMENT_DEPOSIT"
    STEAM_DEPOSIT = "STEAM_DEPOSIT"
    ITEM_OFFICIAL_BUY = "ITEM_OFFICIAL_BUY"
    ITEM_DEFAULT_PRIORITY = "ITEM_DEFAULT_PRIORITY"
    ITEM_PREMIUM_PRIORITY = "ITEM_PREMIUM_PRIORITY"
    ITEM_VIP_PRIORITY = "ITEM_VIP_PRIORITY"
    ITEM_CUSTOM_PRIORITY = "ITEM_CUSTOM_PRIORITY"
    MANUAL_BALANCE_INCREASE = "MANUAL_BALANCE_INCREASE"
    MANUAL_BALANCE_DECREASE = "MANUAL_BALANCE_DECREASE"


class TransactionProvider(OpenEnum):
    LOCAL = "LOCAL"
    BANK_CARD = "BANK_CARD"
    BANK_CARD_ALL = "BANK_CARD_ALL"
    BANK_CARD_RU = "BANK_CARD_RU"
    BANK_CARD_BY = "BANK_CARD_BY"
    BANK_CARD_KZ = "BANK_CARD_KZ"
    SBP = "SBP"
    MOBILE = "MOBILE"
    QIWI = "QIWI"
    YMONEY = "YMONEY"
    WEBMONEY = "WEBMONEY"
    PAYPAL = "PAYPAL"
    APPLE_PAY = "APPLE_PAY"
    GOOGLE_PAY = "GOOGLE_PAY"
    CRYPTO = "CRYPTO"
    USDT = "USDT"
    TRC20 = "TRC20"
    ERC20 = "ERC20"
    TON = "TON"
    ENOT = "ENOT"
    UNITPAY = "UNITPAY"
    PAYMART = "PAYMART"
    RURUPAY = "RURUPAY"
    PROMO_CODE = "PROMO_CODE"
    PENDING_INCOME = "PENDING_INCOME"
    TESTPAY = "TESTPAY"


class TransactionPaymentMethod(OpenEnum):
    RUB = "RUB"
    EUR = "EUR"
    MIR = "MIR"
    VISA_MASTERCARD = "VISA_MASTERCARD"
    ERIP = "ERIP"
    MTS = "MTS"
    BEELINE = "BEELINE"
    MEGAFON = "MEGAFON"
    TELE2 = "TELE2"
    YOTA = "YOTA"


class PaymentGateway(OpenEnum):
    PLAYEROK = "PLAYEROK"
    MANUAL = "MANUAL"
    YOOKASSA = "YOOKASSA"
    ROBOKASSA = "ROBOKASSA"
    FREE_KASSA = "FREE_KASSA"
    PAYMASTER = "PAYMASTER"
    PAYSELECTION = "PAYSELECTION"
    PAYPAL = "PAYPAL"
    PAYPALYCH = "PAYPALYCH"
    CRYPTOMUS = "CRYPTOMUS"
    HELEKET = "HELEKET"
    EXNODE = "EXNODE"
    LAVA = "LAVA"
    ENOT = "ENOT"
    UNITPAY = "UNITPAY"
    YMONEY = "YMONEY"
    QIWI = "QIWI"
    TOME = "TOME"
    TESTPAY = "TESTPAY"


class BankCardType(OpenEnum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    MIR = "MIR"
    UNIONPAY = "UNIONPAY"
    JCB = "JCB"
    AMERICAN_EXPRESS = "AMERICAN_EXPRESS"
    DISCOVER = "DISCOVER"
    UNKNOWN = "UNKNOWN"


class BankCardStatus(OpenEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class NotificationProviderId(OpenEnum):
    EMAIL = "EMAIL"
    PUSH = "PUSH"
    TELEGRAM = "TELEGRAM"
    VK = "VK"
    WS = "WS"


class PaymentCurrency(OpenEnum):
    RUB = "RUB"
    BYN = "BYN"
    KZT = "KZT"
    USD = "USD"


class TransactionForm(OpenEnum):
    """Для чего подбираются способы оплаты."""

    BALANCE = "BALANCE"
    ITEM = "ITEM"
    PREMIUM = "PREMIUM"
    STEAM_TOP_UP = "STEAM_TOP_UP"
    FRAGMENT_TOP_UP = "FRAGMENT_TOP_UP"


class MessageTemplateType(OpenEnum):
    ACTIVE_DEAL_PROBLEM = "ACTIVE_DEAL_PROBLEM"
    FINISHED_DEAL_PROBLEM = "FINISHED_DEAL_PROBLEM"
    SUPPORT = "SUPPORT"
    ITEM_MODERATION = "ITEM_MODERATION"
    WARNING = "WARNING"
    BAN = "BAN"


class FundsProtectionCodeType(OpenEnum):
    """Зачем запрашивается код защиты средств."""

    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    WITHDRAW = "WITHDRAW"
    WALLET_PAYMENT = "WALLET_PAYMENT"
    STEAM_TOP_UP = "STEAM_TOP_UP"
    FRAGMENT_STARS = "FRAGMENT_STARS"


class UserRole(OpenEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    DEVELOPER = "DEVELOPER"
    MODERATOR = "MODERATOR"
    POSTMODERATOR = "POSTMODERATOR"
    SUPPORT = "SUPPORT"
    SECURITY = "SECURITY"
    POSTSECURITY = "POSTSECURITY"
    CHECKER = "CHECKER"
    MONITORING = "MONITORING"
    ACCOUNTANT = "ACCOUNTANT"
    ADV_MANAGER = "ADV_MANAGER"
    ADV_DIRECTOR = "ADV_DIRECTOR"
    GAMES_AND_APPS = "GAMES_AND_APPS"
    OFFICIAL_SELLER = "OFFICIAL_SELLER"
    OFFICIAL_SELLER_ADMIN = "OFFICIAL_SELLER_ADMIN"
    SYSTEM_SELLER = "SYSTEM_SELLER"


class GameType(OpenEnum):
    GAME = "GAME"
    MOBILE_GAME = "MOBILE_GAME"
    APPLICATION = "APPLICATION"


class GameCategoryDataFieldType(OpenEnum):
    ITEM_DATA = "ITEM_DATA"
    OBTAINING_DATA = "OBTAINING_DATA"


class SortDirection(OpenEnum):
    ASC = "ASC"
    DESC = "DESC"
