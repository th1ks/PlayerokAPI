# Пополнение, PL-токены, Fragment, Steam

## Пополнение баланса

Сначала смотрим, чем можно платить:

```python
for provider in await acc.payments.providers():
    print(provider.id, provider.name, provider.fee)
    if provider.incoming:
        print("  от", provider.incoming.min, "до", provider.incoming.max)
```

Провайдеров можно сузить под конкретную задачу:

```python
from PlayerokAPI.enums import TransactionForm

await acc.payments.providers(form=TransactionForm.STEAM_TOP_UP)
await acc.payments.payment_methods("BANK_CARD")
```

Дальше создаём платёж и получаем адрес платёжной страницы:

```python
url = await acc.payments.create_payment_url(
    1000,
    "SBP",
    payment_method="RUB",
    email="mail@example.com",
)
print(url)
```

Платит пользователь уже в браузере. Результат придёт событием
{attr}`~PlayerokAPI.EventType.NEW_TRANSACTION`.

## Карты

```python
for card in await acc.payments.cards():
    print(card.masked, card.card_type, card.status, card.is_chosen)

await acc.payments.set_chosen_card(card_id)  # основная для выплат
await acc.payments.delete_card(card_id)
```

Привязка новой карты начинается с верификации — площадка вернёт адрес,
на котором пользователь подтвердит карту:

```python
url = await acc.payments.verify_card(1.0)
```

## PL-токены

```python
await acc.pl_tokens.balance()
await acc.pl_tokens.history(limit=50)
await acc.pl_tokens.apply_promo_code("WELCOME")

rates = await acc.pl_tokens.cashback_config()
print(rates["steam"], rates["fragment"])
```

Конфигурация кэшбэка публичная и доступна без токена.

## Telegram Stars (Fragment)

```python
config = await acc.fragment.config()
print(config["pricePerStar"], config["minStars"], config["maxStars"])

await acc.fragment.validate_username("durov")
await acc.fragment.buy("durov", 50)
```

`buy` списывает с баланса Playerok, `buy_external` — платит внешним
провайдером.

## Steam

```python
await acc.steam.check_payment_possibility("steam_login")
await acc.steam.currency_rate("KZT", "RUB")
await acc.steam.create_deposit("SBP", 500, account="steam_login")
```

:::{note}
Ручки Steam, `/deals/create`, `/chats/uncensor-message` и
`/funds-protection/send-email-code` принимают только
`multipart/form-data` и отвечают `415` на JSON. Библиотека это
учитывает — ничего настраивать не нужно.
:::

## Защита средств

Если включена, площадка требует код с почты на операции, которые тратят
баланс: покупка товара, пополнение Steam, покупка звёзд, вывод средств.
Оплата внешним провайдером кода не требует.

```python
from PlayerokAPI.enums import FundsProtectionCodeType

me = await acc.get_me()
if me.is_funds_protection_active:
    await acc.misc.send_funds_protection_code(FundsProtectionCodeType.STEAM_TOP_UP)
    await acc.steam.create_deposit("LOCAL", 500, account="login", extra={"confirmationCode": code})
```

Типы кодов: `WALLET_PAYMENT`, `STEAM_TOP_UP`, `FRAGMENT_STARS`, `WITHDRAW`,
а также `ENABLE` и `DISABLE` для самого переключателя.

## Лотереи

```python
lottery = await acc.lottery.active()
if lottery:
    pools = await acc.lottery.pools(lottery["lotteryId"])
    await acc.lottery.claim_daily(lottery["lotteryId"])
```

Покупка билетов идемпотентна: ключ уходит в заголовке `idempotency-key`,
и повтор того же запроса не спишет деньги дважды.

```python
await acc.lottery.buy_tickets(lottery_id, pool_id, 3, idempotency_key="my-key-1")
```

Если ключ не задать, библиотека сгенерирует новый — и тогда повтор будет
новой покупкой.

## Файлы

Загрузка идёт в три шага, но наружу это один вызов:

```python
file_id = await acc.files.upload_path("screenshot.png")
file_id = await acc.files.upload(data, "pic.png", content_type="image/png")
```

Полученный идентификатор принимают `imagesIds` сообщения,
`attachmentIds` товара и `avatarId` профиля.
