"""Профиль, баланс и последние продажи.

python examples/profile.py
"""

from __future__ import annotations

import asyncio
import os

from PlayerokAPI import Account, ItemDealDirection


async def main() -> None:
    token = os.environ["PLAYEROK_TOKEN"]

    async with Account(token=token) as acc:
        me = await acc.get_me()
        balance = me.balance

        print(f"{me.username}  ({me.role})")
        if balance:
            print(f"  доступно:    {balance.available:.2f} ₽")
            print(f"  заморожено:  {balance.frozen:.2f} ₽")
            print(f"  в пути:      {balance.pending_income:.2f} ₽")
        print(f"  отзывов:     {me.testimonial_counter}")
        print(f"  непрочитано: {me.unread_chats_counter}")

        sales = await acc.deals.search(
            filter={"direction": ItemDealDirection.OUT.value},
            first=5,
        )
        print(f"\nПоследние продажи ({sales.total_count} всего):")
        for deal in sales:
            name = deal.item.name if deal.item else "—"
            print(f"  {deal.status}  {name}")


if __name__ == "__main__":
    asyncio.run(main())
