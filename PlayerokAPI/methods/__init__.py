"""Клиентские методы API."""

from .auth import AuthMethods, OtpResult
from .chats import ChatsMethods
from .games import GamesMethods
from .items import ItemsMethods
from .viewer import ViewerMethods

__all__ = [
    "AuthMethods",
    "ChatsMethods",
    "GamesMethods",
    "ItemsMethods",
    "OtpResult",
    "ViewerMethods",
]
