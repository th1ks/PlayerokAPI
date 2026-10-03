"""Игры и их категории."""

from __future__ import annotations

from typing import Any

from ..exceptions import PlayerokError
from ..transport.graphql import GraphQLTransport
from ..types import Game, GameCategory, Page

__all__ = ["GamesMethods"]

_GAME_FIELDS = """
    id slug name type description tags isNew createdAt
    logo { id url } banner { id url }
"""
_CATEGORY_FIELDS = "id slug name gameId categoryId obtaining feeMultiplier"
_CATEGORY_DETAIL_FIELDS = """
    id slug name gameId categoryId obtaining feeMultiplier
    instructionForBuyer instructionForSeller autoConfirmPeriod
    options { id group label type field value multiple }
"""

_LIST_GAMES = f"""
query Games($pagination: Pagination, $filter: GameFilter) {{
    games(pagination: $pagination, filter: $filter) {{
        edges {{ node {{ {_GAME_FIELDS} }} }}
        pageInfo {{ startCursor endCursor hasNextPage hasPreviousPage }}
        totalCount
    }}
}}
"""
_GET_GAME = f"""
query Game($id: UUID, $slug: String) {{
    game(id: $id, slug: $slug) {{
        {_GAME_FIELDS}
        categories {{ {_CATEGORY_FIELDS} }}
    }}
}}
"""
_GET_CATEGORY = f"""
query GameCategory($id: UUID, $slug: String) {{
    gameCategory(id: $id, slug: $slug) {{ {_CATEGORY_DETAIL_FIELDS} }}
}}
"""


class GamesMethods:
    def __init__(self, graphql: GraphQLTransport) -> None:
        self._graphql = graphql

    async def search(
        self, *, name: str | None = None, first: int = 20, after: str | None = None
    ) -> Page[Game]:
        """Найти игры по имени с курсорной пагинацией."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _LIST_GAMES,
            {
                "pagination": {"first": first, "after": after},
                "filter": {"name": name} if name else {},
            },
            operation_name="Games",
        )
        return Page.from_connection(_object(data, "games"), Game)

    async def get(self, *, game_id: str | None = None, slug: str | None = None) -> Game:
        """Получить игру и список её категорий по id или slug."""
        _one_identifier(game_id, slug)
        data = await self._graphql.execute(
            _GET_GAME,
            {"id": game_id, "slug": slug},
            operation_name="Game",
        )
        return Game.from_dict(_object(data, "game"))

    async def categories(
        self, *, game_id: str | None = None, slug: str | None = None
    ) -> list[GameCategory]:
        """Получить категории конкретной игры."""
        return (await self.get(game_id=game_id, slug=slug)).categories

    async def get_category(
        self, *, category_id: str | None = None, slug: str | None = None
    ) -> GameCategory:
        _one_identifier(category_id, slug)
        data = await self._graphql.execute(
            _GET_CATEGORY,
            {"id": category_id, "slug": slug},
            operation_name="GameCategory",
        )
        return GameCategory.from_dict(_object(data, "gameCategory"))


def _one_identifier(identifier: str | None, slug: str | None) -> None:
    if bool(identifier) == bool(slug):
        raise ValueError("Укажите ровно один из id или slug")


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
