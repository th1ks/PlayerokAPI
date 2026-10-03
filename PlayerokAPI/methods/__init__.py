"""Клиентские методы API."""

from .auth import AuthMethods, OtpResult
from .chats import ChatsMethods
from .deals import DealsMethods
from .games import GamesMethods
from .items import ItemsMethods
from .testimonials import TestimonialsMethods
from .transactions import TransactionsMethods
from .viewer import ViewerMethods

__all__ = [
    "AuthMethods",
    "ChatsMethods",
    "DealsMethods",
    "GamesMethods",
    "ItemsMethods",
    "OtpResult",
    "TestimonialsMethods",
    "TransactionsMethods",
    "ViewerMethods",
]
