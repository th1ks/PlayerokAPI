from __future__ import annotations

import httpx
import pytest
import respx

from PlayerokAPI.common.endpoints import BASE_URLS, GRAPHQL_URL, Service
from PlayerokAPI.exceptions import (
    AuthRequiredError,
    GraphQLError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
)
from PlayerokAPI.transport import GraphQLTransport, HttpTransport, RestTransport, Upload

PUBLIC = BASE_URLS[Service.PUBLIC]
BFF = BASE_URLS[Service.BFF]


@pytest.fixture
async def http() -> HttpTransport:
    transport = HttpTransport(token="tok", retries=1)
    yield transport
    await transport.aclose()


@respx.mock
async def test_token_goes_as_cookie(http: HttpTransport) -> None:
    route = respx.get(f"{PUBLIC}/user-geo").mock(
        return_value=httpx.Response(200, json={"country": "NL"})
    )
    rest = RestTransport(http)

    assert await rest.get(Service.PUBLIC, "/user-geo") == {"country": "NL"}
    assert "token=tok" in route.calls.last.request.headers["cookie"]


@respx.mock
async def test_bff_gets_bearer_header(http: HttpTransport) -> None:
    route = respx.get(f"{BFF}/viewer").mock(return_value=httpx.Response(200, json={"id": "1"}))
    rest = RestTransport(http)

    await rest.get(Service.BFF, "/viewer")
    assert route.calls.last.request.headers["authorization"] == "Bearer tok"


@respx.mock
async def test_path_params_are_substituted(http: HttpTransport) -> None:
    route = respx.post(f"{PUBLIC}/item/abc-1/republish").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    rest = RestTransport(http)

    await rest.post(Service.PUBLIC, "/item/{id}/republish", path_params={"id": "abc-1"})
    assert route.called


@respx.mock
async def test_envelope_is_unwrapped(http: HttpTransport) -> None:
    respx.get(f"{PUBLIC}/fragment/deposits/count").mock(
        return_value=httpx.Response(200, json={"success": True, "data": 1074915})
    )
    rest = RestTransport(http)

    assert await rest.get(Service.PUBLIC, "/fragment/deposits/count") == 1074915


@respx.mock
async def test_plain_object_is_not_unwrapped(http: HttpTransport) -> None:
    respx.get(f"{PUBLIC}/user-geo").mock(return_value=httpx.Response(200, json={"country": "NL"}))
    rest = RestTransport(http)

    assert await rest.get(Service.PUBLIC, "/user-geo") == {"country": "NL"}


@respx.mock
async def test_404_raises_not_found(http: HttpTransport) -> None:
    respx.get(f"{PUBLIC}/nope").mock(
        return_value=httpx.Response(
            404,
            json={"statusCode": 404, "message": "not found", "errors": [{"message": "not found"}]},
        )
    )
    rest = RestTransport(http)

    with pytest.raises(NotFoundError) as info:
        await rest.get(Service.PUBLIC, "/nope")
    assert info.value.message == "not found"


@respx.mock
async def test_401_raises_unauthorized(http: HttpTransport) -> None:
    respx.get(f"{BFF}/viewer").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized", "statusCode": 401})
    )
    rest = RestTransport(http)

    with pytest.raises(UnauthorizedError):
        await rest.get(Service.BFF, "/viewer")


@respx.mock
async def test_429_is_retried_then_raised(http: HttpTransport) -> None:
    route = respx.get(f"{PUBLIC}/user-geo").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "slow"})
    )
    rest = RestTransport(http)

    with pytest.raises(RateLimitError):
        await rest.get(Service.PUBLIC, "/user-geo")
    assert route.call_count == 2  # первая попытка плюс один повтор


@respx.mock
async def test_5xx_on_get_is_retried_and_succeeds(http: HttpTransport) -> None:
    route = respx.get(f"{PUBLIC}/user-geo")
    route.side_effect = [
        httpx.Response(502, text="bad gateway"),
        httpx.Response(200, json={"country": "RU"}),
    ]
    rest = RestTransport(http)

    assert await rest.get(Service.PUBLIC, "/user-geo") == {"country": "RU"}
    assert route.call_count == 2


@respx.mock
async def test_5xx_on_post_is_not_retried(http: HttpTransport) -> None:
    route = respx.post(f"{PUBLIC}/deals/create").mock(return_value=httpx.Response(500, text="oops"))
    rest = RestTransport(http)

    with pytest.raises(ServerError):
        await rest.post(Service.PUBLIC, "/deals/create", json={})
    assert route.call_count == 1


async def test_auth_required_without_token() -> None:
    transport = HttpTransport(token=None)
    rest = RestTransport(transport)
    try:
        with pytest.raises(AuthRequiredError):
            await rest.get(Service.BFF, "/viewer", auth=True)
    finally:
        await transport.aclose()


@respx.mock
async def test_feature_flag_value(http: HttpTransport) -> None:
    respx.post("https://playerok.com/rest-api/feature-flags").mock(
        return_value=httpx.Response(
            200,
            json={
                "evaluationResults": {
                    "ws-url": {
                        "variantKey": "on",
                        "variantAttachment": {"url": "wss://ws.playerok.com/graphql"},
                    },
                    "api-url": {"variantKey": None},
                }
            },
        )
    )
    rest = RestTransport(http)

    assert await rest.flag_value("ws-url") == {"url": "wss://ws.playerok.com/graphql"}
    assert await rest.flag_value("api-url") is None


@respx.mock
async def test_graphql_returns_data(http: HttpTransport) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"data": {"viewer": {"id": "u1"}}})
    )
    gql = GraphQLTransport(http)

    data = await gql.execute("query viewer { viewer { id } }", operation_name="viewer")
    assert data == {"viewer": {"id": "u1"}}
    assert route.calls.last.request.headers["apollo-require-preflight"] == "true"


@respx.mock
async def test_graphql_errors_raise(http: HttpTransport) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(
            200,
            json={"errors": [{"message": "Нет доступа", "extensions": {"code": "FORBIDDEN"}}]},
        )
    )
    gql = GraphQLTransport(http)

    with pytest.raises(GraphQLError) as info:
        await gql.execute("query x { x }", operation_name="x")
    assert info.value.code == "FORBIDDEN"
    assert "Нет доступа" in str(info.value)


@respx.mock
async def test_graphql_upload_is_multipart(http: HttpTransport) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=httpx.Response(200, json={"data": {"createItem": {"id": "i1"}}})
    )
    gql = GraphQLTransport(http)

    await gql.execute(
        "mutation createItem($input: CreateItemInput!, $attachments: [Upload!]) { createItem }",
        {"input": {"name": "x"}, "attachments": [None]},
        operation_name="createItem",
        uploads={"attachments.0": Upload(b"png-bytes", "a.png", "image/png")},
    )

    body = route.calls.last.request.content
    assert b'name="operations"' in body
    assert b'name="map"' in body
    assert b"png-bytes" in body


@respx.mock
async def test_multipart_form_is_sent_for_415_endpoints(http: HttpTransport) -> None:
    route = respx.post(f"{PUBLIC}/deals/create").mock(
        return_value=httpx.Response(200, json={"id": "d1"})
    )
    rest = RestTransport(http)

    await rest.post(
        Service.PUBLIC,
        "/deals/create",
        form={"itemId": "i1", "transactionProviderId": "LOCAL", "skip": None},
    )

    request = route.calls.last.request
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    body = request.content
    assert b'name="itemId"' in body
    assert b"i1" in body
    assert b'name="skip"' not in body
