"""Отзывы о сделках."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..common.utils import drop_none
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport
from ..types import Page, Testimonial

__all__ = ["TestimonialsMethods"]

_FIELDS = """
    id status text rating createdAt updatedAt
    deal { id status direction }
    creator { id username avatarURL }
    user { id username avatarURL }
"""
_PAGE_INFO = "startCursor endCursor hasNextPage hasPreviousPage"
_SEARCH = f"""
query Testimonials($pagination: Pagination, $sort: Sort, $filter: TestimonialFilter!) {{
    testimonials(pagination: $pagination, sort: $sort, filter: $filter) {{
        edges {{ node {{ {_FIELDS} }} }}
        pageInfo {{ {_PAGE_INFO} }}
        totalCount
    }}
}}
"""
_CREATE = f"""
mutation CreateTestimonial($input: CreateTestimonialInput!) {{
    createTestimonial(input: $input) {{ {_FIELDS} }}
}}
"""
_UPDATE = f"""
mutation UpdateTestimonial($input: UpdateTestimonialInput!) {{
    updateTestimonial(input: $input) {{ {_FIELDS} }}
}}
"""
_REMOVE = f"""
mutation RemoveTestimonial($id: UUID!) {{
    removeTestimonial(id: $id) {{ {_FIELDS} }}
}}
"""


class TestimonialsMethods:
    def __init__(self, graphql: GraphQLTransport) -> None:
        self._graphql = graphql

    async def search(
        self,
        *,
        filter: Mapping[str, Any] | None = None,
        sort: Mapping[str, Any] | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Page[Testimonial]:
        """Отзывы с фильтром `TestimonialFilter` и курсорной пагинацией."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        data = await self._graphql.execute(
            _SEARCH,
            {
                "filter": dict(filter or {}),
                "sort": dict(sort) if sort else None,
                "pagination": drop_none({"first": first, "after": after}),
            },
            operation_name="Testimonials",
        )
        return Page.from_connection(_object(data, "testimonials"), Testimonial)

    async def create(
        self,
        deal_id: str,
        rating: int,
        *,
        text: str | None = None,
        fields: Mapping[str, Any] | None = None,
    ) -> Testimonial:
        """Оставить отзыв по сделке."""
        if not 1 <= rating <= 5:
            raise ValueError("rating должен быть от 1 до 5")
        body = dict(fields or {})
        body.update(drop_none({"dealId": deal_id, "rating": rating, "text": text}))
        data = await self._graphql.execute(
            _CREATE, {"input": body}, operation_name="CreateTestimonial", auth=True
        )
        return Testimonial.from_dict(_object(data, "createTestimonial"))

    async def update(self, testimonial_id: str, changes: Mapping[str, Any]) -> Testimonial:
        """Изменить свой отзыв; ключи changes соответствуют `UpdateTestimonialInput`."""
        if not changes:
            raise ValueError("Передайте изменения отзыва")
        body = dict(changes)
        body["id"] = testimonial_id
        data = await self._graphql.execute(
            _UPDATE, {"input": body}, operation_name="UpdateTestimonial", auth=True
        )
        return Testimonial.from_dict(_object(data, "updateTestimonial"))

    async def remove(self, testimonial_id: str) -> Testimonial:
        """Удалить свой отзыв."""
        data = await self._graphql.execute(
            _REMOVE,
            {"id": testimonial_id},
            operation_name="RemoveTestimonial",
            auth=True,
        )
        return Testimonial.from_dict(_object(data, "removeTestimonial"))


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
