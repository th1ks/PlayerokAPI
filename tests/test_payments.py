from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from PlayerokAPI import Account
from PlayerokAPI.common.endpoints import BASE_URLS, GRAPHQL_URL, Service
from PlayerokAPI.enums import (
    BankCardType,
    NotificationProviderId,
    TransactionForm,
    TransactionProvider,
)
from PlayerokAPI.exceptions import PlayerokError

BFF = BASE_URLS[Service.BFF]
PUBLIC = BASE_URLS[Service.PUBLIC]


@pytest.fixture
async def acc() -> Account:
    account = Account(token="tok", retries=0)
    yield account
    await account.aclose()


def gql(data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"data": data})


def sent(route: respx.Route) -> dict[str, Any]:
    return json.loads(route.calls.last.request.content)


# --- провайдеры и способы оплаты ----------------------------------------


@respx.mock
async def test_providers(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql(
            {
                "transactionProviders": [
                    {
                        "id": "SBP",
                        "name": "СБП",
                        "fee": 0.0,
                        "currency": "RUB",
                        "limits": {"incoming": {"min": 100, "max": 50000}},
                        "paymentMethods": [{"id": "RUB", "name": "Рубли", "providerId": "SBP"}],
                    }
                ]
            }
        )
    )

    providers = await acc.payments.providers(form=TransactionForm.BALANCE)

    assert len(providers) == 1
    provider = providers[0]
    assert provider.id is TransactionProvider.SBP
    assert provider.incoming is not None and provider.incoming.max == 50000
    assert provider.payment_methods[0].id == "RUB"
    assert sent(route)["variables"]["filter"] == {
        "direction": "IN",
        "transactionForm": "BALANCE",
    }


@respx.mock
async def test_payment_methods_filter(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql({"transactionPaymentMethods": [{"id": "MIR", "providerId": "BANK_CARD"}]})
    )

    methods = await acc.payments.payment_methods(TransactionProvider.BANK_CARD)

    assert methods[0].provider_id is TransactionProvider.BANK_CARD
    assert sent(route)["variables"]["filter"] == {"providerId": "BANK_CARD"}


# --- пополнение ----------------------------------------------------------


@respx.mock
async def test_create_payment_url(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql({"createPaymentURL": "https://pay.example.com/abc"})
    )

    url = await acc.payments.create_payment_url(
        1000,
        TransactionProvider.SBP,
        payment_method="RUB",
        email="a@b.c",
        promocode="SALE",
    )

    assert url == "https://pay.example.com/abc"
    payload = sent(route)["variables"]["input"]
    assert payload["value"] == 1000
    assert payload["provider"] == "SBP"
    assert payload["promocode"] == "SALE"
    assert payload["providerData"] == {"paymentMethodId": "RUB"}
    assert payload["userData"] == {"email": "a@b.c"}
    # Пустые группы не отправляются.
    assert "currency" not in payload


@respx.mock
async def test_create_payment_url_without_extras(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(return_value=gql({"createPaymentURL": "https://pay/x"}))
    await acc.payments.create_payment_url(500, "LOCAL")
    payload = sent(route)["variables"]["input"]
    assert "providerData" not in payload
    assert "userData" not in payload


@respx.mock
async def test_create_payment_url_without_url_raises(acc: Account) -> None:
    respx.post(GRAPHQL_URL).mock(return_value=gql({"createPaymentURL": ""}))
    with pytest.raises(PlayerokError):
        await acc.payments.create_payment_url(100, "LOCAL")


async def test_create_payment_url_validates_value(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.payments.create_payment_url(0, "LOCAL")


# --- карты ---------------------------------------------------------------


@respx.mock
async def test_cards(acc: Account) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=gql(
            {
                "verifiedCards": {
                    "edges": [
                        {
                            "node": {
                                "id": "c1",
                                "cardFirstSix": "427901",
                                "cardLastFour": "1234",
                                "cardType": "VISA",
                                "status": "VERIFIED",
                                "isChosen": True,
                            }
                        }
                    ],
                    "pageInfo": {"hasNextPage": False},
                    "totalCount": 1,
                }
            }
        )
    )

    cards = await acc.payments.cards()

    assert cards[0].card_type is BankCardType.VISA
    assert cards[0].is_chosen is True
    assert cards[0].masked.endswith("1234")


@respx.mock
async def test_set_chosen_and_delete_card(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL)
    route.side_effect = [gql({"setChosenCard": True}), gql({"deleteCard": True})]

    assert await acc.payments.set_chosen_card("c1") is True
    assert await acc.payments.delete_card("c1") is True


@respx.mock
async def test_verify_card(acc: Account) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=gql({"verifyCard": {"redirectUrl": "https://verify/x"}})
    )
    assert await acc.payments.verify_card(1.0) == "https://verify/x"


# --- уведомления ---------------------------------------------------------


@respx.mock
async def test_notification_channels_resolve_user_id(acc: Account) -> None:
    respx.get(f"{BFF}/viewer").mock(return_value=httpx.Response(200, json={"id": "u1"}))
    respx.get(f"{BFF}/viewer/balance").mock(return_value=httpx.Response(200, json={"value": 0}))
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql(
            {"notificationProviders": [{"id": "TELEGRAM", "name": "Telegram", "enabled": True}]}
        )
    )

    channels = await acc.notifications.channels()

    assert channels[0].id is NotificationProviderId.TELEGRAM
    assert sent(route)["variables"]["userId"] == "u1"


@respx.mock
async def test_notification_enable(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql({"enableNotificationProvider": {"id": "EMAIL", "enabled": True}})
    )

    channel = await acc.notifications.enable(NotificationProviderId.EMAIL, user_id="u1")

    assert channel.enabled is True
    assert sent(route)["variables"]["input"] == {"providerId": "EMAIL", "userId": "u1"}


@respx.mock
async def test_telegram_bot_link(acc: Account) -> None:
    respx.post(GRAPHQL_URL).mock(
        return_value=gql({"getTelegramBotLink": {"subscribeURL": "https://t.me/bot?start=x"}})
    )
    assert await acc.notifications.telegram_bot_link() == "https://t.me/bot?start=x"


# --- остаток viewer ------------------------------------------------------


@respx.mock
async def test_viewer_chosen_card(acc: Account) -> None:
    respx.get(f"{BFF}/viewer/chosen-card").mock(
        return_value=httpx.Response(200, json={"id": "c1", "cardLastFour": "1234"})
    )
    card = await acc.viewer.chosen_card()
    assert card is not None and card.last_four == "1234"


@respx.mock
async def test_viewer_chosen_card_absent(acc: Account) -> None:
    respx.get(f"{BFF}/viewer/chosen-card").mock(return_value=httpx.Response(200, json=None))
    assert await acc.viewer.chosen_card() is None


@respx.mock
async def test_two_factor_flow(acc: Account) -> None:
    request = respx.post(f"{PUBLIC}/viewer/two-factor/enable/request-email-code").mock(
        return_value=httpx.Response(200, json={"sent": True})
    )
    verify = respx.post(f"{PUBLIC}/viewer/two-factor/enable/verify-email-code").mock(
        return_value=httpx.Response(200, json={"token": "t-1"})
    )
    confirm = respx.post(f"{PUBLIC}/viewer/two-factor/enable/confirm").mock(
        return_value=httpx.Response(200, json={"enabled": True})
    )

    await acc.viewer.request_two_factor_email_code()
    token = (await acc.viewer.verify_two_factor_email_code("123456"))["token"]
    await acc.viewer.confirm_two_factor(token, "654321")

    assert request.called
    assert json.loads(verify.calls.last.request.content) == {"code": "123456"}
    assert json.loads(confirm.calls.last.request.content) == {
        "token": "t-1",
        "totpCode": "654321",
    }


async def test_two_factor_validates_input(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.viewer.verify_two_factor_email_code("")
    with pytest.raises(ValueError):
        await acc.viewer.confirm_two_factor("t", "")


# --- проблемы по сделке --------------------------------------------------


@respx.mock
async def test_deal_problem_types(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql(
            {
                "messageTemplates": {
                    "edges": [{"node": {"id": "p1", "title": "Товар не выдан"}}],
                    "pageInfo": {"hasNextPage": False},
                    "totalCount": 1,
                }
            }
        )
    )

    types = await acc.deals.problem_types()

    assert types[0].title == "Товар не выдан"
    assert sent(route)["variables"]["filter"] == {"type": "ACTIVE_DEAL_PROBLEM"}


@respx.mock
async def test_deal_problem_types_finished(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql({"messageTemplates": {"edges": [], "pageInfo": {}, "totalCount": 0}})
    )
    await acc.deals.problem_types(finished=True)
    assert sent(route)["variables"]["filter"] == {"type": "FINISHED_DEAL_PROBLEM"}


@respx.mock
async def test_report_problem(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(
        return_value=gql({"reportDealProblem": {"id": "d1", "hasProblem": True}})
    )

    deal = await acc.deals.report_problem("d1", "p1", "Продавец не выходит на связь")

    assert deal.has_problem is True
    assert sent(route)["variables"]["input"] == {
        "dealId": "d1",
        "problemTypeId": "p1",
        "description": "Продавец не выходит на связь",
    }


async def test_report_problem_validates_input(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.deals.report_problem("d1", "", "текст")


# --- убранное админское --------------------------------------------------


def test_message_edit_and_delete_are_gone(acc: Account) -> None:
    assert not hasattr(acc.chats, "edit")
    assert not hasattr(acc.chats, "remove")


# --- защита средств ------------------------------------------------------


@respx.mock
async def test_funds_protection_flag_from_viewer(acc: Account) -> None:
    respx.get(f"{BFF}/viewer").mock(
        return_value=httpx.Response(
            200, json={"id": "u1", "username": "seller", "isFundsProtectionActive": True}
        )
    )
    respx.get(f"{BFF}/viewer/balance").mock(return_value=httpx.Response(200, json={"value": 0}))

    me = await acc.get_me()

    assert me.is_funds_protection_active is True


@respx.mock
async def test_funds_protection_flag_absent_means_off(acc: Account) -> None:
    respx.get(f"{BFF}/viewer").mock(return_value=httpx.Response(200, json={"id": "u1"}))
    respx.get(f"{BFF}/viewer/balance").mock(return_value=httpx.Response(200, json={"value": 0}))

    assert (await acc.get_me()).is_funds_protection_active is False


@respx.mock
async def test_set_funds_protection(acc: Account) -> None:
    route = respx.post(GRAPHQL_URL).mock(return_value=gql({"setFundsProtectionActive": True}))

    assert await acc.viewer.set_funds_protection(True, "123456") is True
    assert sent(route)["variables"]["input"] == {
        "isFundsProtectionActive": True,
        "confirmationCode": "123456",
    }


async def test_set_funds_protection_requires_code(acc: Account) -> None:
    with pytest.raises(ValueError):
        await acc.viewer.set_funds_protection(False, "")


@respx.mock
async def test_purchase_passes_confirmation_code(acc: Account) -> None:
    route = respx.post(f"{PUBLIC}/deals/create").mock(
        return_value=httpx.Response(200, json={"transaction": {"id": "t1"}})
    )

    await acc.deals.create("i1", "LOCAL", confirmation_code="123456")

    body = route.calls.last.request.content
    assert b'name="confirmationCode"' in body
    assert b"123456" in body
