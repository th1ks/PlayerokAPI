"""Единая точка входа в клиент Playerok."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import httpx

from .common.endpoints import DEFAULT_USER_AGENT
from .methods import (
    AuthMethods,
    ChatsMethods,
    DealsMethods,
    FilesMethods,
    FragmentMethods,
    GamesMethods,
    ItemsMethods,
    LotteryMethods,
    MiscMethods,
    PlTokensMethods,
    SteamMethods,
    TestimonialsMethods,
    TransactionsMethods,
    ViewerMethods,
)
from .transport import GraphQLTransport, HttpTransport, RestTransport, WebSocketTransport
from .types import ChatMessage, User, UserBalance
from .updater import EventType, Listener, PollingRunner

__all__ = ["Account"]


class Account:
    def __init__(
        self,
        token: str | None = None,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 20.0,
        retries: int = 3,
        rate_limit: tuple[int, float] | None = None,
        proxy: str | None = None,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.http = HttpTransport(
            token,
            user_agent=user_agent,
            timeout=timeout,
            retries=retries,
            rate_limit=rate_limit,
            proxy=proxy,
            headers=headers,
            client=client,
        )
        self.rest = RestTransport(self.http)
        self.graphql = GraphQLTransport(self.http)
        self.ws = WebSocketTransport(self.http)
        self.auth = AuthMethods(self.rest)
        self.viewer = ViewerMethods(self.rest)
        self.games = GamesMethods(self.graphql)
        self.items = ItemsMethods(self.graphql, self.rest)
        self.chats = ChatsMethods(self.graphql)
        self.deals = DealsMethods(self.graphql, self.rest)
        self.testimonials = TestimonialsMethods(self.graphql)
        self.transactions = TransactionsMethods(self.graphql)
        self.files = FilesMethods(self.rest)
        self.pl_tokens = PlTokensMethods(self.rest)
        self.fragment = FragmentMethods(self.rest)
        self.steam = SteamMethods(self.rest)
        self.lottery = LotteryMethods(self.rest)
        self.misc = MiscMethods(self.rest)
        self._me: User | None = None
        self._me_token: str | None = None

    @property
    def token(self) -> str | None:
        return self.http.token

    @token.setter
    def token(self, value: str | None) -> None:
        self.http.token = value
        self._me = None
        self._me_token = None

    @property
    def id(self) -> str | None:
        return self._me.id if self._me and self._me_token == self.token else None

    async def get_me(self) -> User:
        self._me = await self.viewer.get_me()
        self._me_token = self.token
        return self._me

    async def send_message(self, chat_id: str, text: str) -> ChatMessage:
        """Короткий путь к `acc.chats.send`."""
        return await self.chats.send(chat_id, text)

    async def get_balance(self) -> UserBalance:
        """Короткий путь к `acc.viewer.get_balance`."""
        return await self.viewer.get_balance()

    def listener(
        self,
        *,
        events: Iterable[EventType] | None = None,
        filters: Mapping[EventType, Mapping[str, Any]] | None = None,
    ) -> Listener:
        """Слушатель событий на подписках WebSocket."""
        return Listener(self, events=events, filters=filters)

    def polling(self, *, interval: float = 5.0) -> PollingRunner:
        """Запасной источник событий для окружений без WebSocket."""
        return PollingRunner(self, interval=interval)

    async def aclose(self) -> None:
        await self.ws.close()
        await self.http.aclose()

    async def __aenter__(self) -> Account:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
