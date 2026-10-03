"""Адреса бэкендов Playerok.

Собрано разбором продакшн-бандла playerok.com и проверкой маршрутов вживую.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "BASE_URLS",
    "BEARER_SERVICES",
    "COOKIE_DOMAIN",
    "DEFAULT_USER_AGENT",
    "FEATURE_FLAGS_URL",
    "GRAPHQL_URL",
    "TOKEN_COOKIE",
    "WEB_ORIGIN",
    "WS_FALLBACK_URL",
    "WS_URL",
    "Service",
]

WEB_ORIGIN = "https://playerok.com"
COOKIE_DOMAIN = ".playerok.com"
TOKEN_COOKIE = "token"

GRAPHQL_URL = f"{WEB_ORIGIN}/graphql"

#: Основной адрес подписок, выдаётся feature-флагом `ws-url`.
WS_URL = "wss://ws.playerok.com/graphql"
#: Старый адрес, на который фронт откатывается, если флаг выключен.
WS_FALLBACK_URL = "wss://playerok.com/subscriptions"

FEATURE_FLAGS_URL = f"{WEB_ORIGIN}/rest-api/feature-flags"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class Service(str, Enum):
    """REST-бэкенды площадки."""

    PUBLIC = "public"
    """Основной публичный REST, авторизация по cookie."""

    BFF = "bff"
    """BFF, тот же токен уходит в заголовке Authorization."""

    AUTH = "auth"
    """Сервис авторизации нового поколения, маршруты /auth/v1/..."""


BASE_URLS: dict[Service, str] = {
    Service.PUBLIC: f"{WEB_ORIGIN}/rest-api/public",
    Service.BFF: "https://bff.playerok.com/rest-api/public",
    Service.AUTH: "https://sapi.playerok.com",
}

#: Кому токен нужен в заголовке Authorization, а не только в cookie.
BEARER_SERVICES = frozenset({Service.BFF})
