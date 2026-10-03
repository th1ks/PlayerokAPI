"""Публичный каталог без авторизации: топ, поиск и курс Fragment.

python examples/catalog.py
"""

from __future__ import annotations

import asyncio

from PlayerokAPI import Account


async def main() -> None:
    # Токен не нужен: всё в этом примере — публичные ручки.
    async with Account() as acc:
        print("Страна по IP:", await acc.misc.user_geo())

        top = await acc.items.top(page_size=5)
        print("\nПопулярное:")
        for item in top:
            game = item.game.name if item.game else "—"
            print(f"  {item.price:>8.0f} ₽  {game:<20} {item.name}")

        found = await acc.items.search(query="steam", first=5)
        print(f"\nПоиск «steam» ({found.total_count} всего):")
        for item in found:
            print(f"  {item.price:>8.0f} ₽  {item.name}")

        config = await acc.fragment.config()
        print(
            f"\nTelegram Stars: {config.get('pricePerStar')} ₽ за звезду, "
            f"от {config.get('minStars')} до {config.get('maxStars')}"
        )

        cashback = await acc.pl_tokens.cashback_config()
        print(
            "Кэшбэк PL-токенами: steam", cashback.get("steam"), "· баланс", cashback.get("balance")
        )


if __name__ == "__main__":
    asyncio.run(main())
