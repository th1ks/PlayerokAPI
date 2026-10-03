from __future__ import annotations

import json

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import GRAPHQL_URL
from PlayerokAPI.exceptions import AuthRequiredError
from PlayerokAPI.transport import Upload


@respx.mock
async def test_chat_list_detail_and_message_pagination() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "chats": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ch1",
                                    "type": "PM",
                                    "participants": [{"id": "u1"}, {"id": "u2"}],
                                    "lastMessage": {"id": "m1", "text": "привет"},
                                }
                            }
                        ],
                        "pageInfo": {"endCursor": "next", "hasNextPage": True},
                        "totalCount": 3,
                    }
                }
            },
        ),
        httpx.Response(200, json={"data": {"chat": {"id": "ch1", "type": "PM"}}}),
        httpx.Response(
            200,
            json={
                "data": {
                    "chatMessages": {
                        "edges": [
                            {
                                "node": {
                                    "id": "m2",
                                    "text": "ответ",
                                    "user": {"id": "u2", "username": "seller"},
                                }
                            }
                        ],
                        "pageInfo": {"startCursor": "older", "hasPreviousPage": True},
                        "totalCount": 4,
                    }
                }
            },
        ),
    ]
    async with Account(token="tok") as account:
        page = await account.chats.search(filter={"type": "PM"}, first=1, after="cursor")
        assert page.total_count == 3 and page.has_next_page
        assert page.items[0].last_message is not None
        assert page.items[0].last_message.chat_id == "ch1"
        chat = await account.chats.get("ch1")
        assert chat.id == "ch1"
        messages = await account.chats.messages("ch1", limit=2, before="before-cursor")
        assert messages.items[0].chat_id == "ch1"
        assert messages.items[0].author_id == "u2"
        assert messages.has_previous_page

    listed = json.loads(route.calls[0].request.content)
    assert listed["variables"] == {
        "pagination": {"first": 1, "after": "cursor"},
        "filter": {"type": "PM"},
    }
    history = json.loads(route.calls[2].request.content)
    assert history["variables"] == {
        "pagination": {"last": 2, "before": "before-cursor"},
        "filter": {"chatId": "ch1"},
    }
    assert "token=tok" in route.calls[0].request.headers["cookie"]


@respx.mock
async def test_send_uploads_image_then_uses_its_id() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={"data": {"uploadChatImageIntoTemporaryStore": {"id": "img1", "url": "u"}}},
        ),
        httpx.Response(
            200,
            json={
                "data": {
                    "createChatMessage": {
                        "id": "m1",
                        "text": "привет",
                        "user": {"id": "u1"},
                        "images": [{"id": "img1", "url": "u"}],
                    }
                }
            },
        ),
    ]
    async with Account(token="tok") as account:
        message = await account.chats.send(
            "ch1", "привет", images=[Upload(b"image-bytes", "a.png", "image/png")]
        )
        assert message.id == "m1" and message.chat_id == "ch1"
        assert message.images[0].id == "img1"

    upload_body = route.calls[0].request.content
    assert b'"variables.file"' in upload_body
    assert b"image-bytes" in upload_body
    assert b'"chatId": "ch1"' in upload_body
    sent = json.loads(route.calls[1].request.content)
    assert sent["variables"]["input"] == {
        "chatId": "ch1",
        "text": "привет",
        "imagesIds": ["img1"],
    }


@respx.mock
async def test_edit_read_and_remove_use_client_mutations() -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"updateChatMessage": {"id": "m1", "text": "новый"}}}),
        httpx.Response(200, json={"data": {"markChatAsRead": {"id": "ch1"}}}),
        httpx.Response(200, json={"data": {"removeChatMessage": {"id": "m1"}}}),
    ]
    async with Account(token="tok") as account:
        assert (await account.chats.edit("m1", "новый")).text == "новый"
        assert (await account.chats.mark_read("ch1")).id == "ch1"
        assert (await account.chats.remove("m1")).id == "m1"

    assert json.loads(route.calls[0].request.content)["variables"]["input"] == {
        "id": "m1",
        "text": "новый",
    }
    assert json.loads(route.calls[1].request.content)["variables"]["input"] == {"chatId": "ch1"}
    assert json.loads(route.calls[2].request.content)["variables"] == {"id": "m1"}


async def test_chat_methods_validate_before_network() -> None:
    async with Account() as account:
        with pytest.raises(AuthRequiredError):
            await account.chats.search()
        with pytest.raises(ValueError):
            await account.chats.send("ch1")
        with pytest.raises(ValueError):
            await account.chats.messages("ch1", before="a", after="b")
