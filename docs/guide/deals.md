# Сделки, отзывы, транзакции

## Список сделок

```python
from PlayerokAPI import ItemDealDirection

purchases = await acc.deals.search(
    filter={"direction": ItemDealDirection.IN.value},
    first=20,
)
sales = await acc.deals.search(
    filter={"direction": ItemDealDirection.OUT.value, "status": ["PAID", "SENT"]},
)
```

`IN` — покупки, деньги уходят со счёта. `OUT` — продажи.
Остальные ключи соответствуют `ItemDealFilter`.

## Одна сделка

```python
deal = await acc.deals.get(deal_id)

deal.status  # ItemDealStatus
deal.is_purchase  # True, если это покупка
deal.item.name
deal.chat_id  # чат со второй стороной
deal.transaction.value
deal.url
```

## Покупка

```python
transaction = await acc.deals.create(
    item_id,
    "LOCAL",  # оплата с баланса
    comment_from_buyer="Здравствуйте, нужен сегодня",
)
print(transaction.id, transaction.status)
```

:::{warning}
Это настоящая покупка: деньги списываются сразу. Запрос уходит один раз
и не повторяется автоматически, даже если сервер ответил ошибкой `5xx`, —
чтобы повтор не создал вторую сделку.
:::

Остальные поля `CreateItemDealInput` передаются через `extra`:

```python
await acc.deals.create(
    item_id,
    "LOCAL",
    extra={"obtainingFields": [{"id": field_id, "value": "nickname"}]},
)
```

## Смена статуса

```python
await acc.deals.update(deal_id, {"status": "CONFIRMED"})
```

Ключи соответствуют `UpdateItemDealInput`.

## Проблема по сделке

Сначала выбирается тип проблемы — площадка хранит их как шаблоны
сообщений, отдельного запроса под них в схеме нет:

```python
for problem in await acc.deals.problem_types():
    print(problem.id, problem.title)

await acc.deals.report_problem(
    deal_id,
    problem_type_id,
    "Продавец не выходит на связь вторые сутки",
)
```

Для завершённых сделок список другой: `problem_types(finished=True)`.

## Отзывы

```python
await acc.testimonials.create(deal_id, 5, text="Всё быстро, спасибо")

page = await acc.testimonials.search(filter={"userId": seller_id}, first=20)
for testimonial in page:
    print(testimonial.rating, testimonial.text)
```

## Транзакции

```python
page = await acc.transactions.search(filter={"direction": "IN"}, first=20)
for transaction in page:
    print(transaction.operation, transaction.value, transaction.status)
```

## Вывод средств

```python
await acc.transactions.withdraw(1000, "BANK_CARD", "4279010000001234")
```

Если у аккаунта включена защита средств, сначала запросите код:

```python
from PlayerokAPI.enums import FundsProtectionCodeType

await acc.misc.send_funds_protection_code(FundsProtectionCodeType.WITHDRAW)
await acc.transactions.withdraw(1000, "BANK_CARD", account, confirmation_code="123456")
```
