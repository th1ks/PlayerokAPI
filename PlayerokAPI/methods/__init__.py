"""Клиентские методы API."""

from .auth import AuthMethods, OtpResult
from .chats import ChatsMethods
from .deals import DealsMethods
from .files import FilesMethods
from .fragment import FragmentMethods
from .games import GamesMethods
from .items import ItemsMethods
from .lottery import LotteryMethods
from .misc import MiscMethods
from .steam import SteamMethods
from .testimonials import TestimonialsMethods
from .tokens import PlTokensMethods
from .transactions import TransactionsMethods
from .viewer import ViewerMethods

__all__ = [
    "AuthMethods",
    "ChatsMethods",
    "DealsMethods",
    "FilesMethods",
    "FragmentMethods",
    "GamesMethods",
    "ItemsMethods",
    "LotteryMethods",
    "MiscMethods",
    "OtpResult",
    "PlTokensMethods",
    "SteamMethods",
    "TestimonialsMethods",
    "TransactionsMethods",
    "ViewerMethods",
]
