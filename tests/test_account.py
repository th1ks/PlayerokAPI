from __future__ import annotations

import json

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import BASE_URLS, Service
from PlayerokAPI.exceptions import TokenError

PUBLIC = BASE_URLS[Service.PUBLIC]
BFF = BASE_URLS[Service.BFF]


@respx.mock
async def test_otp_login_captures_cookie_and_uses_it_for_viewer() -> None:
    send = respx.post(f"{PUBLIC}/auth/send-otp").mock(return_value=httpx.Response(200, json={}))
    confirm = respx.post(f"{PUBLIC}/auth/confirm-otp").mock(
        return_value=httpx.Response(
            200,
            json={"requiresTwoFactor": False},
            headers={"set-cookie": "token=new-token; Path=/; HttpOnly"},
        )
    )
    viewer = respx.get(f"{BFF}/viewer").mock(
        return_value=httpx.Response(200, json={"id": "u1", "username": "alice"})
    )
    balance = respx.get(f"{BFF}/viewer/balance").mock(
        return_value=httpx.Response(200, json={"available": 42})
    )
    logout = respx.post(f"{BFF}/auth/logout").mock(return_value=httpx.Response(200, json={}))

    async with Account(token="old-token") as account:
        await account.auth.send_otp("alice@example.com")
        result = await account.auth.confirm_otp("alice@example.com", "123456")
        assert result.token == account.token == "new-token"
        assert not result.requires_two_factor
        assert json.loads(send.calls.last.request.content) == {"email": "alice@example.com"}
        assert json.loads(confirm.calls.last.request.content) == {
            "email": "alice@example.com",
            "otpCode": "123456",
        }

        me = await account.get_me()
        assert me.username == "alice"
        assert me.balance is not None and me.balance.available == 42
        assert account.id == "u1"
        assert viewer.calls.last.request.headers["authorization"] == "Bearer new-token"
        assert balance.called

        await account.auth.logout()
        assert account.token is None
        assert account.id is None
        assert not any(cookie.name == "token" for cookie in account.http.client.cookies.jar)
        assert logout.called


@respx.mock
async def test_second_factor_uses_session_token_then_saves_cookie() -> None:
    respx.post(f"{PUBLIC}/auth/confirm-otp").mock(
        return_value=httpx.Response(
            200,
            json={
                "requiresTwoFactor": True,
                "secondFactorSession": {"token": "pending-token", "expiresAt": "2026-10-03"},
            },
        )
    )
    second = respx.post(f"{PUBLIC}/auth/confirm-second-factor").mock(
        return_value=httpx.Response(
            200,
            json={},
            headers={"set-cookie": "token=final-token; Domain=.playerok.com; Path=/; HttpOnly"},
        )
    )
    async with Account() as account:
        result = await account.auth.confirm_otp("alice@example.com", "123456")
        assert result.requires_two_factor
        assert result.second_factor_session == {
            "token": "pending-token",
            "expiresAt": "2026-10-03",
        }
        assert account.token is None

        token = await account.auth.confirm_second_factor("pending-token", "654321")
        assert token == account.token == "final-token"
        assert json.loads(second.calls.last.request.content) == {
            "token": "pending-token",
            "totpCode": "654321",
        }


@respx.mock
async def test_otp_does_not_reuse_an_existing_token_without_new_credentials() -> None:
    respx.post(f"{PUBLIC}/auth/confirm-otp").mock(
        return_value=httpx.Response(200, json={"requiresTwoFactor": False})
    )
    async with Account(token="old-token") as account:
        with pytest.raises(TokenError):
            await account.auth.confirm_otp("alice@example.com", "123456")
        assert account.token == "old-token"


@respx.mock
async def test_otp_accepts_token_reissued_in_response_cookie() -> None:
    respx.post(f"{PUBLIC}/auth/confirm-otp").mock(
        return_value=httpx.Response(
            200,
            json={"requiresTwoFactor": False},
            headers={"set-cookie": "token=same-token; Path=/; HttpOnly"},
        )
    )
    async with Account(token="same-token") as account:
        result = await account.auth.confirm_otp("alice@example.com", "123456")
        assert result.token == "same-token"


@respx.mock
async def test_viewer_methods_use_documented_rest_fields() -> None:
    username = respx.get(f"{PUBLIC}/viewer/username-availability").mock(
        return_value=httpx.Response(200, json={"isTaken": True})
    )
    avatar = respx.put(f"{BFF}/viewer/avatar").mock(
        return_value=httpx.Response(200, json={"avatarURL": "https://example.com/a.png"})
    )
    async with Account(token="tok") as account:
        assert await account.viewer.is_username_taken("alice")
        assert username.calls.last.request.url.params["username"] == "alice"
        await account.viewer.set_avatar("file-1")
        assert avatar.calls.last.request.headers["authorization"] == "Bearer tok"
        assert json.loads(avatar.calls.last.request.content) == {"avatarId": "file-1"}
