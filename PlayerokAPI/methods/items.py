"""Поиск, создание и управление товарами."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..common.endpoints import Service
from ..common.utils import drop_none
from ..enums import ItemPriority, ItemStatus
from ..exceptions import PlayerokError
from ..transport import GraphQLTransport, RestTransport, Upload
from ..types import Item, ItemPriorityStatus, ItemProfile, Page
from . import fields

__all__ = ["ItemsMethods"]

_PROFILE_FIELDS = fields.ITEM_PROFILE
_ITEM_FIELDS = fields.ITEM

# priceForIncrease и feeMultiplier у части тарифов приходят пустыми и валятся
# на non-null в схеме сервера, поэтому их не запрашиваем.
_PRIORITY_STATUSES = """
query ItemPriorityStatuses($itemId: UUID, $price: NonNegativeFloat!) {
    itemPriorityStatuses(itemId: $itemId, price: $price) {
        id name type price period boosterType
        priceRange { min max }
    }
}
"""

_SEARCH = f"""
query Items($filter: ItemFilter, $pagination: Pagination, $sort: Sort) {{
    items(filter: $filter, pagination: $pagination, sort: $sort) {{
        edges {{ node {{ {_PROFILE_FIELDS} }} }}
        pageInfo {{ startCursor endCursor hasNextPage hasPreviousPage }}
        totalCount
    }}
}}
"""
_GET = f"""
query Item($id: UUID, $slug: String) {{
    item(id: $id, slug: $slug) {{ {_ITEM_FIELDS} }}
}}
"""
_CREATE = f"""
mutation CreateItem($input: CreateItemInput!, $attachments: [Upload!]) {{
    createItem(input: $input, attachments: $attachments) {{ {_ITEM_FIELDS} }}
}}
"""
_UPDATE = f"""
mutation UpdateItem($input: UpdateItemInput!, $addedAttachments: [Upload!]) {{
    updateItem(input: $input, addedAttachments: $addedAttachments) {{ {_ITEM_FIELDS} }}
}}
"""
_PUBLISH = f"""
mutation PublishItem($input: PublishItemInput!) {{
    publishItem(input: $input) {{ {_ITEM_FIELDS} }}
}}
"""
_PROMOTE = f"""
mutation IncreaseItemPriorityStatus($input: PublishItemInput!) {{
    increaseItemPriorityStatus(input: $input) {{ {_ITEM_FIELDS} }}
}}
"""


class ItemsMethods:
    def __init__(self, graphql: GraphQLTransport, rest: RestTransport) -> None:
        self._graphql = graphql
        self._rest = rest

    async def top(
        self,
        *,
        category_id: str | None = None,
        exclude_item_ids: Sequence[str] = (),
        hide_sensitive_items_for_telegram: bool | None = None,
        page_size: int | None = None,
        after: str | None = None,
    ) -> Page[ItemProfile]:
        """Популярные товары из клиентского REST-каталога."""
        return await self._catalog_listing(
            "top",
            category_id,
            exclude_item_ids,
            hide_sensitive_items_for_telegram,
            page_size,
            after,
        )

    async def official(
        self,
        *,
        category_id: str | None = None,
        exclude_item_ids: Sequence[str] = (),
        hide_sensitive_items_for_telegram: bool | None = None,
        page_size: int | None = None,
        after: str | None = None,
    ) -> Page[ItemProfile]:
        """Официальные товары из клиентского REST-каталога."""
        return await self._catalog_listing(
            "official",
            category_id,
            exclude_item_ids,
            hide_sensitive_items_for_telegram,
            page_size,
            after,
        )

    async def _catalog_listing(
        self,
        kind: str,
        category_id: str | None,
        exclude_item_ids: Sequence[str],
        hide_sensitive_items_for_telegram: bool | None,
        page_size: int | None,
        after: str | None,
    ) -> Page[ItemProfile]:
        if page_size is not None and page_size < 1:
            raise ValueError("page_size должен быть положительным")
        filters = drop_none(
            {
                "categoryIds": [category_id] if category_id else None,
                "excludeItemIds": list(exclude_item_ids) or None,
                "hideSensitiveItemsForTelegram": hide_sensitive_items_for_telegram,
            }
        )
        payload = await self._rest.post(
            Service.CATALOG,
            f"/v1/catalog/items/{kind}",
            json={"filter": filters, "page": drop_none({"size": page_size, "cursor": after})},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise PlayerokError("Неожиданный ответ REST-каталога")
        items = payload["items"]
        if not all(isinstance(item, dict) for item in items):
            raise PlayerokError("Неожиданный товар в ответе REST-каталога")
        return Page(
            items=[ItemProfile.from_dict(item) for item in items],
            end_cursor=payload.get("endCursor"),
            has_next_page=bool(payload.get("hasNextPage")),
        )

    async def search(
        self,
        *,
        query: str | None = None,
        game_id: str | None = None,
        category_id: str | None = None,
        user_id: str | None = None,
        status: ItemStatus | str | None = None,
        only_official: bool | None = None,
        filter: Mapping[str, Any] | None = None,
        sort: Mapping[str, Any] | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Page[ItemProfile]:
        """Искать товары с курсорной пагинацией."""
        if first < 1:
            raise ValueError("first должен быть положительным")
        filters = dict(filter or {})
        filters.update(
            drop_none(
                {
                    "searchQuery": query,
                    "gameId": game_id,
                    "gameCategoryId": category_id,
                    "userId": user_id,
                    "status": status.value if isinstance(status, ItemStatus) else status,
                    "onlyOfficial": only_official,
                }
            )
        )
        if not filters:
            raise ValueError("Для поиска укажите хотя бы один фильтр")
        data = await self._graphql.execute(
            _SEARCH,
            {
                "filter": filters,
                "pagination": {"first": first, "after": after},
                "sort": dict(sort) if sort else None,
            },
            operation_name="Items",
        )
        return Page.from_connection(_object(data, "items"), ItemProfile)

    async def get(self, *, item_id: str | None = None, slug: str | None = None) -> Item:
        """Получить товар по id или slug."""
        if bool(item_id) == bool(slug):
            raise ValueError("Укажите ровно один из item_id или slug")
        data = await self._graphql.execute(
            _GET,
            {"id": item_id, "slug": slug},
            operation_name="Item",
        )
        return Item.from_dict(_object(data, "item"))

    async def create(
        self,
        *,
        game_category_id: str,
        name: str,
        description: str,
        price: float,
        fields: Mapping[str, Any] | None = None,
        attachments: Sequence[Upload] = (),
    ) -> Item:
        """Создать черновик; поля категории можно передать через fields."""
        body = dict(fields or {})
        body.update(
            {
                "gameCategoryId": game_category_id,
                "name": name,
                "description": description,
                "price": price,
            }
        )
        variables, uploads = _attachment_variables("attachments", attachments)
        variables["input"] = body
        data = await self._graphql.execute(
            _CREATE,
            variables,
            uploads=uploads or None,
            operation_name="CreateItem",
            auth=True,
        )
        return Item.from_dict(_object(data, "createItem"))

    async def update(
        self,
        item_id: str,
        changes: Mapping[str, Any],
        *,
        added_attachments: Sequence[Upload] = (),
    ) -> Item:
        """Изменить товар; ключи changes соответствуют UpdateItemInput."""
        body = dict(changes)
        body["id"] = item_id
        variables, uploads = _attachment_variables("addedAttachments", added_attachments)
        variables["input"] = body
        data = await self._graphql.execute(
            _UPDATE,
            variables,
            uploads=uploads or None,
            operation_name="UpdateItem",
            auth=True,
        )
        return Item.from_dict(_object(data, "updateItem"))

    async def priority_statuses(
        self,
        price: float,
        *,
        item_id: str | None = None,
    ) -> list[ItemPriorityStatus]:
        """Тарифы публикации для товара такой цены.

        Цена тарифа зависит от цены товара, поэтому она обязательна.
        У обычного тарифа (`DEFAULT`) цена нулевая — публикация бесплатна.
        """
        if price < 0:
            raise ValueError("price не может быть отрицательным")
        data = await self._graphql.execute(
            _PRIORITY_STATUSES,
            drop_none({"itemId": item_id, "price": price}),
            operation_name="ItemPriorityStatuses",
            auth=True,
        )
        statuses = data.get("itemPriorityStatuses")
        if not isinstance(statuses, list):
            raise PlayerokError("Пустой или неожиданный ответ itemPriorityStatuses")
        return [ItemPriorityStatus.from_dict(item) for item in statuses if isinstance(item, dict)]

    async def publish(
        self,
        item_id: str,
        *,
        priority_statuses: Sequence[str] | None = None,
        transaction_provider_id: str = "LOCAL",
        options: Mapping[str, Any] | None = None,
    ) -> Item:
        """Опубликовать товар.

        Без `priority_statuses` берётся бесплатный обычный тариф: библиотека
        сама подтянет цену товара и найдёт `DEFAULT`. Платный тариф задаётся
        явно — идентификаторы отдаёт `priority_statuses()`.

        `transaction_provider_id` сервер требует всегда, даже на бесплатном
        тарифе, поэтому по умолчанию стоит оплата с баланса.
        """
        statuses = (
            list(priority_statuses)
            if priority_statuses is not None
            else [await self._free_priority_status(item_id)]
        )
        return await self._publish_operation(
            _PUBLISH,
            "PublishItem",
            "publishItem",
            item_id,
            statuses,
            transaction_provider_id,
            options,
        )

    async def _free_priority_status(self, item_id: str) -> str:
        """Идентификатор бесплатного тарифа для конкретного товара."""
        item = await self.get(item_id=item_id)
        for status in await self.priority_statuses(item.price, item_id=item_id):
            if status.type is ItemPriority.DEFAULT:
                return status.id
        raise PlayerokError("Площадка не предложила бесплатный тариф публикации")

    async def promote(
        self,
        item_id: str,
        *,
        priority_statuses: Sequence[str],
        transaction_provider_id: str,
        options: Mapping[str, Any] | None = None,
    ) -> Item:
        """Повысить приоритет опубликованного товара."""
        return await self._publish_operation(
            _PROMOTE,
            "IncreaseItemPriorityStatus",
            "increaseItemPriorityStatus",
            item_id,
            priority_statuses,
            transaction_provider_id,
            options,
        )

    async def discontinue(self, item_id: str) -> None:
        """Снять товар с продажи через клиентский REST."""
        await self._rest.post(
            Service.PUBLIC,
            "/item/{id}/discontinue",
            path_params={"id": item_id},
            auth=True,
        )

    async def republish(self, item_id: str) -> None:
        """Повторно выставить ранее снятый товар."""
        await self._rest.post(
            Service.PUBLIC,
            "/item/{id}/republish",
            path_params={"id": item_id},
            auth=True,
        )

    async def _publish_operation(
        self,
        document: str,
        operation_name: str,
        result_key: str,
        item_id: str,
        priority_statuses: Sequence[str],
        transaction_provider_id: str,
        options: Mapping[str, Any] | None,
    ) -> Item:
        body = dict(options or {})
        body.update(
            {
                "itemId": item_id,
                "priorityStatuses": list(priority_statuses),
                "transactionProviderId": transaction_provider_id,
            }
        )
        data = await self._graphql.execute(
            document,
            {"input": body},
            operation_name=operation_name,
            auth=True,
        )
        return Item.from_dict(_object(data, result_key))


def _attachment_variables(
    name: str, attachments: Sequence[Upload]
) -> tuple[dict[str, Any], dict[str, Upload]]:
    if not attachments:
        return {}, {}
    return (
        {name: [None] * len(attachments)},
        {f"{name}.{index}": upload for index, upload in enumerate(attachments)},
    )


def _object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlayerokError(f"Пустой или неожиданный ответ {key}")
    return value
