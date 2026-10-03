from __future__ import annotations

import json

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import BASE_URLS, GRAPHQL_URL, Service
from PlayerokAPI.exceptions import AuthRequiredError


@respx.mock
async def test_deals_list_get_and_update() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "deals": {
                        "edges": [{"node": {"id": "d1", "status": "PENDING"}}],
                        "pageInfo": {"endCursor": "next", "hasNextPage": True},
                        "totalCount": 2,
                    }
                }
            },
        ),
        httpx.Response(200, json={"data": {"deal": {"id": "d1", "chat": {"id": "ch1"}}}}),
        httpx.Response(200, json={"data": {"updateDeal": {"id": "d1", "status": "DONE"}}}),
    ]
    async with Account(token="tok") as account:
        page = await account.deals.search(filter={"userId": "u1"}, first=1, after="prev")
        assert page.total_count == 2 and page.has_next_page
        assert page.items[0].id == "d1"
        assert (await account.deals.get("d1")).chat_id == "ch1"
        assert (await account.deals.update("d1", {"status": "DONE"})).id == "d1"

    listed = json.loads(route.calls[0].request.content)
    # sort не задан — переменная не отправляется вовсе, а не уходит как null
    assert listed["variables"] == {
        "filter": {"userId": "u1"},
        "pagination": {"first": 1, "after": "prev"},
    }
    updated = json.loads(route.calls[2].request.content)
    assert updated["variables"]["input"] == {"id": "d1", "status": "DONE"}


@respx.mock
async def test_create_deal_uses_single_multipart_rest_request() -> None:
    route = respx.post(f"{BASE_URLS[Service.PUBLIC]}/deals/create").mock(
        return_value=httpx.Response(200, json={"transaction": {"id": "t1", "value": 100}})
    )
    async with Account(token="tok", retries=3) as account:
        transaction = await account.deals.create(
            "i1", "LOCAL", comment_from_buyer="привет", extra={"obtainingFields": []}
        )
        assert transaction.id == "t1" and transaction.value == 100
    assert route.call_count == 1
    request = route.calls.last.request
    assert request.headers["content-type"].startswith("multipart/form-data;")
    assert b'name="itemId"' in request.content
    assert b'name="transactionProviderId"' in request.content
    assert b"LOCAL" in request.content
    assert b'name="obtainingFields"' in request.content


@respx.mock
async def test_testimonials_search_create_update_remove() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "testimonials": {
                        "edges": [{"node": {"id": "r1", "rating": 5}}],
                        "pageInfo": {},
                        "totalCount": 1,
                    }
                }
            },
        ),
        httpx.Response(200, json={"data": {"createTestimonial": {"id": "r2", "rating": 4}}}),
        httpx.Response(200, json={"data": {"updateTestimonial": {"id": "r2", "rating": 5}}}),
        httpx.Response(200, json={"data": {"removeTestimonial": {"id": "r2"}}}),
    ]
    async with Account(token="tok") as account:
        assert (await account.testimonials.search(first=1)).items[0].rating == 5
        assert (await account.testimonials.create("d1", 4, text="хорошо")).rating == 4
        assert (await account.testimonials.update("r2", {"rating": 5})).rating == 5
        assert (await account.testimonials.remove("r2")).id == "r2"

    created = json.loads(route.calls[1].request.content)
    assert created["variables"]["input"] == {"dealId": "d1", "rating": 4, "text": "хорошо"}


@respx.mock
async def test_transactions_search_get_and_withdraw() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "transactions": {
                        "edges": [{"node": {"id": "t1", "value": 100}}],
                        "pageInfo": {"endCursor": "next", "hasNextPage": True},
                        "totalCount": 2,
                    }
                }
            },
        ),
        httpx.Response(200, json={"data": {"transaction": {"id": "t1", "fee": 3}}}),
        httpx.Response(200, json={"data": {"requestWithdrawal": {"id": "t2", "value": 50}}}),
    ]
    async with Account(token="tok") as account:
        page = await account.transactions.search(filter={"userId": "u1"}, first=1)
        assert page.items[0].id == "t1" and page.has_next_page
        assert (await account.transactions.get("t1")).fee == 3
        assert (await account.transactions.withdraw(50, "LOCAL", "card-number")).id == "t2"

    withdrawn = json.loads(route.calls[2].request.content)
    assert withdrawn["variables"]["input"] == {
        "value": 50,
        "provider": "LOCAL",
        "account": "card-number",
    }


async def test_new_methods_validate_before_network() -> None:
    async with Account() as account:
        with pytest.raises(AuthRequiredError):
            await account.deals.get("d1")
        with pytest.raises(ValueError):
            await account.deals.create("", "LOCAL")
        with pytest.raises(ValueError):
            await account.testimonials.create("d1", 6)
        with pytest.raises(ValueError):
            await account.transactions.withdraw(0, "LOCAL", "card-number")
