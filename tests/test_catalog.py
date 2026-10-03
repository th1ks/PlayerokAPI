from __future__ import annotations

import json

import httpx
import pytest
import respx

from PlayerokAPI import Account, ItemPriority, ItemStatus
from PlayerokAPI.common.endpoints import BASE_URLS, GRAPHQL_URL, Service
from PlayerokAPI.exceptions import AuthRequiredError, PlayerokError
from PlayerokAPI.transport import Upload


@pytest.mark.parametrize("kind", ["top", "official"])
@respx.mock
async def test_rest_catalog_listing_and_cursor(kind: str) -> None:
    route = respx.post(f"{BASE_URLS[Service.CATALOG]}/v1/catalog/items/{kind}").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "i1",
                        "slug": "item-slug",
                        "name": "Товар",
                        "price": 100,
                        "isOfficial": True,
                        "seller": {
                            "id": "u1",
                            "username": "Playerok",
                            "avatarUrl": "https://example.com/avatar.png",
                        },
                    }
                ],
                "endCursor": "next-cursor",
                "hasNextPage": True,
            },
        )
    )
    async with Account() as account:
        method = account.items.top if kind == "top" else account.items.official
        page = await method(
            category_id="c1",
            exclude_item_ids=["i0"],
            hide_sensitive_items_for_telegram=False,
            page_size=2,
            after="previous-cursor",
        )

    assert page.end_cursor == "next-cursor" and page.has_next_page
    assert page.items[0].is_official is True
    assert page.items[0].user is not None
    assert page.items[0].user.username == "Playerok"
    assert page.items[0].user.avatar_url == "https://example.com/avatar.png"
    assert json.loads(route.calls.last.request.content) == {
        "filter": {
            "categoryIds": ["c1"],
            "excludeItemIds": ["i0"],
            "hideSensitiveItemsForTelegram": False,
        },
        "page": {"size": 2, "cursor": "previous-cursor"},
    }


async def test_rest_catalog_rejects_nonpositive_page_size() -> None:
    async with Account() as account:
        with pytest.raises(ValueError):
            await account.items.top(page_size=0)


@respx.mock
async def test_games_and_categories_use_cursor_connections() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "games": {
                        "edges": [{"node": {"id": "g1", "slug": "roblox", "name": "Roblox"}}],
                        "pageInfo": {"endCursor": "next", "hasNextPage": True},
                        "totalCount": 2,
                    }
                }
            },
        ),
        httpx.Response(
            200,
            json={
                "data": {
                    "game": {
                        "id": "g1",
                        "slug": "roblox",
                        "name": "Roblox",
                        "categories": [{"id": "c1", "name": "Robux", "gameId": "g1"}],
                    }
                }
            },
        ),
        httpx.Response(
            200,
            json={
                "data": {
                    "gameCategory": {
                        "id": "c1",
                        "name": "Robux",
                        "options": [{"id": "o1", "field": "amount", "value": "100"}],
                    }
                }
            },
        ),
    ]
    async with Account() as account:
        page = await account.games.search(name="Roblox", first=1)
        assert page.items[0].slug == "roblox"
        assert page.end_cursor == "next" and page.has_next_page
        categories = await account.games.categories(slug="roblox")
        assert categories[0].id == "c1"
        assert categories[0].game_id == "g1"
        category = await account.games.get_category(category_id="c1")
        assert category.options[0]["field"] == "amount"

    assert json.loads(route.calls[0].request.content)["variables"]["filter"] == {"name": "Roblox"}
    assert json.loads(route.calls[1].request.content)["variables"]["slug"] == "roblox"


@respx.mock
async def test_item_search_and_detail_parse_models() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "items": {
                        "edges": [
                            {
                                "node": {
                                    "__typename": "ForeignItemProfile",
                                    "id": "i1",
                                    "name": "Robux",
                                    "price": 100,
                                    "status": "APPROVED",
                                }
                            }
                        ],
                        "pageInfo": {"endCursor": "next", "hasNextPage": True},
                        "totalCount": 12,
                    }
                }
            },
        ),
        httpx.Response(
            200,
            json={"data": {"item": {"__typename": "ForeignItem", "id": "i1", "name": "Robux"}}},
        ),
    ]
    async with Account() as account:
        page = await account.items.search(
            query="robux", game_id="g1", status=ItemStatus.APPROVED, first=1, after="before"
        )
        assert page.total_count == 12
        assert page.items[0].price == 100
        item = await account.items.get(item_id=page.items[0].id)
        assert item.id == "i1" and not item.is_mine

    variables = json.loads(route.calls[0].request.content)["variables"]
    assert variables["filter"] == {
        "searchQuery": "robux",
        "gameId": "g1",
        "status": "APPROVED",
    }
    assert variables["pagination"] == {"first": 1, "after": "before"}


@respx.mock
async def test_create_upload_and_discontinue_use_correct_transports() -> None:
    create = respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"data": {"createItem": {"id": "i1"}}})
    )
    discontinue = respx.post(f"{BASE_URLS[Service.PUBLIC]}/item/i1/discontinue").mock(
        return_value=httpx.Response(200, json={})
    )
    async with Account(token="tok") as account:
        item = await account.items.create(
            game_category_id="c1",
            name="Robux",
            description="Описание",
            price=100,
            fields={"comment": "Автовыдача"},
            attachments=[Upload(b"image-bytes", "a.png", "image/png")],
        )
        assert item.id == "i1"
        await account.items.discontinue(item.id)

    body = create.calls.last.request.content
    assert b'"gameCategoryId": "c1"' in body
    assert b'"variables.attachments.0"' in body
    assert b"image-bytes" in body
    assert discontinue.calls.last.request.headers["cookie"].startswith("token=tok")


@respx.mock
async def test_publish_and_promote_send_required_input() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"publishItem": {"id": "i1"}}}),
        httpx.Response(200, json={"data": {"increaseItemPriorityStatus": {"id": "i1"}}}),
    ]
    async with Account(token="tok") as account:
        await account.items.publish(
            "i1", priority_statuses=["priority-1"], transaction_provider_id="LOCAL"
        )
        await account.items.promote(
            "i1", priority_statuses=["priority-2"], transaction_provider_id="LOCAL"
        )

    first = json.loads(route.calls[0].request.content)
    second = json.loads(route.calls[1].request.content)
    assert first["operationName"] == "PublishItem"
    assert second["operationName"] == "IncreaseItemPriorityStatus"
    assert first["variables"]["input"] == {
        "itemId": "i1",
        "priorityStatuses": ["priority-1"],
        "transactionProviderId": "LOCAL",
    }
    assert second["variables"]["input"]["priorityStatuses"] == ["priority-2"]


async def test_item_mutations_require_token() -> None:
    async with Account() as account:
        with pytest.raises(AuthRequiredError):
            await account.items.publish("i1", priority_statuses=[], transaction_provider_id="LOCAL")


# --- тарифы публикации ---------------------------------------------------


def _statuses_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": {
                "itemPriorityStatuses": [
                    {
                        "id": "prem-1",
                        "name": "Премиум",
                        "type": "PREMIUM",
                        "price": 49,
                        "period": 30,
                        "priceRange": {"min": 1000, "max": 2500},
                    },
                    {"id": "def-1", "name": "Обычный", "type": "DEFAULT", "price": 0, "period": 30},
                ]
            }
        },
    )


@respx.mock
async def test_priority_statuses() -> None:
    route = respx.post(GRAPHQL_URL).mock(return_value=_statuses_response())
    async with Account(token="tok") as account:
        statuses = await account.items.priority_statuses(1000)

    assert [s.type for s in statuses] == [ItemPriority.PREMIUM, ItemPriority.DEFAULT]
    assert statuses[0].price == 49
    assert statuses[0].is_free is False
    assert statuses[1].is_free is True
    assert json.loads(route.calls.last.request.content)["variables"] == {"price": 1000}


async def test_priority_statuses_rejects_negative_price() -> None:
    async with Account(token="tok") as account:
        with pytest.raises(ValueError):
            await account.items.priority_statuses(-1)


@respx.mock
async def test_publish_picks_free_tier_by_default() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"item": {"id": "i1", "price": 1000}}}),
        _statuses_response(),
        httpx.Response(200, json={"data": {"publishItem": {"id": "i1", "status": "APPROVED"}}}),
    ]

    async with Account(token="tok") as account:
        item = await account.items.publish("i1")

    assert item.id == "i1"
    published = json.loads(route.calls[2].request.content)["variables"]["input"]
    assert published["priorityStatuses"] == ["def-1"]
    assert published["transactionProviderId"] == "LOCAL"


@respx.mock
async def test_publish_with_explicit_paid_tier_skips_lookup() -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"data": {"publishItem": {"id": "i1"}}})
    )

    async with Account(token="tok") as account:
        await account.items.publish(
            "i1", priority_statuses=["prem-1"], transaction_provider_id="SBP"
        )

    assert route.call_count == 1
    published = json.loads(route.calls.last.request.content)["variables"]["input"]
    assert published["priorityStatuses"] == ["prem-1"]
    assert published["transactionProviderId"] == "SBP"


@respx.mock
async def test_publish_without_free_tier_raises() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"item": {"id": "i1", "price": 1000}}}),
        httpx.Response(
            200,
            json={
                "data": {
                    "itemPriorityStatuses": [
                        {"id": "prem-1", "type": "PREMIUM", "price": 49},
                    ]
                }
            },
        ),
    ]

    async with Account(token="tok") as account:
        with pytest.raises(PlayerokError):
            await account.items.publish("i1")
