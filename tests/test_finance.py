from __future__ import annotations

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import BASE_URLS, Service
from PlayerokAPI.enums import FundsProtectionCodeType, TransactionProvider
from PlayerokAPI.exceptions import AuthRequiredError

PUBLIC = BASE_URLS[Service.PUBLIC]
BFF = BASE_URLS[Service.BFF]


@pytest.fixture
async def acc() -> Account:
    account = Account(token="tok", retries=0)
    yield account
    await account.aclose()


# --- файлы ---------------------------------------------------------------


@respx.mock
async def test_upload_goes_through_three_steps(acc: Account) -> None:
    slot = respx.get(f"{BFF}/file/v1/upload-url").mock(
        return_value=httpx.Response(
            200,
            json={
                "url": "storage.example.com/bucket",
                "file_id": "f-1",
                "fields": {"key": "uploads/f-1", "policy": "p"},
            },
        )
    )
    storage = respx.post("https://storage.example.com/bucket").mock(
        return_value=httpx.Response(204)
    )
    confirm = respx.post(f"{BFF}/file/v1/confirm-upload").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    file_id = await acc.files.upload(b"png-bytes", "pic.png")

    assert file_id == "f-1"
    assert slot.called and storage.called and confirm.called
    body = storage.calls.last.request.content
    assert b'name="key"' in body
    assert b'name="file"; filename="pic.png"' in body
    assert b"png-bytes" in body
    assert confirm.calls.last.request.content == b'{"id":"f-1"}'


@respx.mock
async def test_upload_accepts_camel_case_file_id(acc: Account) -> None:
    respx.get(f"{BFF}/file/v1/upload-url").mock(
        return_value=httpx.Response(200, json={"url": "https://s/x", "fileId": "f-2", "fields": {}})
    )
    respx.post("https://s/x").mock(return_value=httpx.Response(204))
    respx.post(f"{BFF}/file/v1/confirm-upload").mock(return_value=httpx.Response(200, json={}))

    assert await acc.files.upload(b"x", "a.bin") == "f-2"


async def test_upload_rejects_empty_file(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.files.upload(b"", "a.bin")


# --- PL-токены -----------------------------------------------------------


@respx.mock
async def test_cashback_config(acc: Account) -> None:
    respx.get(f"{PUBLIC}/pl-tokens/cashback-config").mock(
        return_value=httpx.Response(200, json={"balance": 20, "steam": 20, "fragment": 30})
    )
    assert (await acc.pl_tokens.cashback_config())["fragment"] == 30


@respx.mock
async def test_promo_code_requires_token() -> None:
    account = Account(token=None)
    try:
        with pytest.raises(AuthRequiredError):
            await account.pl_tokens.apply_promo_code("ABC")
    finally:
        await account.aclose()


# --- Fragment ------------------------------------------------------------


@respx.mock
async def test_fragment_count_unwraps_envelope(acc: Account) -> None:
    respx.get(f"{PUBLIC}/fragment/deposits/count").mock(
        return_value=httpx.Response(200, json={"success": True, "data": 1074915})
    )
    assert await acc.fragment.deposits_count() == 1074915


@respx.mock
async def test_fragment_buy(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/fragment/buy").mock(
        return_value=httpx.Response(200, json={"success": True, "data": {"id": "d1"}})
    )
    assert await acc.fragment.buy("durov", 50) == {"id": "d1"}
    assert route.calls.last.request.content == b'{"username":"durov","starsAmount":50}'


async def test_fragment_buy_validates_amount(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.fragment.buy("durov", 0)


# --- Steam ---------------------------------------------------------------


@respx.mock
async def test_steam_create_deposit_is_multipart(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/steam/create-deposit").mock(
        return_value=httpx.Response(200, json={"success": True, "data": {"id": "s1"}})
    )

    await acc.steam.create_deposit(TransactionProvider.SBP, 500, account="player")

    request = route.calls.last.request
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.content
    assert b"SBP" in body
    assert b'name="value"' in body
    assert b'name="promocode"' not in body


@respx.mock
async def test_steam_currency_rate_query(acc: Account) -> None:
    route = respx.get(f"{PUBLIC}/steam/currency-rate").mock(
        return_value=httpx.Response(200, json={"rate": 1.1})
    )
    await acc.steam.currency_rate("KZT", "RUB")
    assert route.calls.last.request.url.params["from"] == "KZT"
    assert route.calls.last.request.url.params["to"] == "RUB"


# --- лотереи -------------------------------------------------------------


@respx.mock
async def test_buy_tickets_sends_idempotency_key(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/lottery/l1/pools/p1/tickets").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    await acc.lottery.buy_tickets("l1", "p1", 3, idempotency_key="key-1")

    assert route.calls.last.request.headers["idempotency-key"] == "key-1"
    assert route.calls.last.request.content == b'{"quantity":3}'


@respx.mock
async def test_buy_tickets_generates_key_when_missing(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/lottery/l1/pools/p1/tickets").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    await acc.lottery.buy_tickets("l1", "p1", 1)
    assert route.calls.last.request.headers["idempotency-key"]


async def test_buy_tickets_validates_quantity(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.lottery.buy_tickets("l1", "p1", 0)


# --- прочее --------------------------------------------------------------


@respx.mock
async def test_user_geo(acc: Account) -> None:
    respx.get(f"{PUBLIC}/user-geo").mock(return_value=httpx.Response(200, json={"country": "NL"}))
    assert await acc.misc.user_geo() == "NL"


@respx.mock
async def test_promo_banners(acc: Account) -> None:
    respx.get(f"{BFF}/promo-banners").mock(
        return_value=httpx.Response(200, json={"items": [{"id": "b1"}]})
    )
    assert await acc.misc.promo_banners() == [{"id": "b1"}]


async def test_quick_deal_widgets_requires_a_filter(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.misc.quick_deal_widgets()


@respx.mock
async def test_funds_protection_code_is_multipart(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/funds-protection/send-email-code").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    await acc.misc.send_funds_protection_code(FundsProtectionCodeType.WITHDRAW)
    assert b"WITHDRAW" in route.calls.last.request.content


@respx.mock
async def test_websocket_url_from_feature_flag(acc: Account) -> None:
    respx.post("https://playerok.com/rest-api/feature-flags").mock(
        return_value=httpx.Response(
            200,
            json={
                "evaluationResults": {
                    "ws-url": {
                        "variantKey": "on",
                        "variantAttachment": {"url": "wss://ws.playerok.com/graphql"},
                    }
                }
            },
        )
    )
    assert await acc.misc.websocket_url() == "wss://ws.playerok.com/graphql"


@respx.mock
async def test_websocket_url_none_when_flag_off(acc: Account) -> None:
    respx.post("https://playerok.com/rest-api/feature-flags").mock(
        return_value=httpx.Response(
            200, json={"evaluationResults": {"ws-url": {"variantKey": "off"}}}
        )
    )
    assert await acc.misc.websocket_url() is None
