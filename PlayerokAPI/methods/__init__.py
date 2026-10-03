"""Клиентские методы API."""

from .auth import AuthMethods, OtpResult
from .viewer import ViewerMethods

__all__ = ["AuthMethods", "OtpResult", "ViewerMethods"]
