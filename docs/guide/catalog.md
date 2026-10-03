# Каталог и товары

## Игры и категории

```python
games = await acc.games.search(name="counter", first=10)
for game in games:
    print(game.slug, game.name, game.items_counter)

game = await acc.games.get(slug="cs2")
for category in await acc.games.categories(game_id=game.id):
    print(category.slug, category.name, category.items_counter)
```

## Поиск товаров

Публичный поиск работает и без токена:

```python
page = await acc.items.search(query="steam", first=20)
print(page.total_count)

for item in page:
    print(item.price, item.name, item.url)
```

Фильтры попроще вынесены в именованные аргументы, остальное —
через `filter`, он соответствует `ItemFilter` из схемы:

```python
await acc.items.search(
    game_id=game.id,
    status=ItemStatus.APPROVED,
    only_official=False,
    filter={"price": {"min": 100, "max": 1000}, "hasDiscount": True},
    sort={"field": "price", "direction": "ASC"},
)
```

## Витрины

Популярное и официальный магазин живут в отдельном REST-сервисе
каталога, поэтому у них своя пагинация по `page_size`:

```python
for item in await acc.items.top(page_size=10):
    print(item.name)

for item in await acc.items.official(category_id=category.id):
    print(item.name)
```

## Один товар

```python
item = await acc.items.get(slug="cool-account")

item.price
item.description
item.status  # ItemStatus
item.is_mine  # сервер отдал реализацию MyItem
item.attachments  # список File
item.data_fields  # поля данных товара
```

Искать можно и по идентификатору: `await acc.items.get(item_id="...")`.

## Создание и публикация

Товар сначала создаётся черновиком, потом публикуется — публикация
платная, поэтому у неё отдельный вызов с выбором тарифа и способа оплаты.

```python
from PlayerokAPI.transport import Upload

item = await acc.items.create(
    game_category_id=category.id,
    name="Аккаунт с 1000 часов",
    description="Полный доступ к почте",
    price=1500,
    attachments=[Upload.from_path("screenshot.png")],
)

await acc.items.publish(
    item.id,
    priority_statuses=[priority_id],
    transaction_provider_id="LOCAL",
)
```

Идентификаторы тарифов берутся из `itemPriorityStatuses` в схеме
площадки; `LOCAL` означает оплату с баланса.

## Изменение

```python
await acc.items.update(item.id, {"price": 1300, "keepInSale": True})
```

Ключи `changes` соответствуют `UpdateItemInput`. Новые вложения —
через `added_attachments`.

## Снятие и возврат в продажу

```python
await acc.items.discontinue(item.id)  # снять с продажи
await acc.items.republish(item.id)  # вернуть
```

Обе ручки REST-овые и ничего не возвращают.

## Продвижение

```python
await acc.items.promote(
    item.id,
    priority_statuses=[vip_priority_id],
    transaction_provider_id="LOCAL",
)
```
