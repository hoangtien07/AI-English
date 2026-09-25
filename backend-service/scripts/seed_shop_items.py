# ruff: noqa: E402

import asyncio
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal
from app.core.shop_catalog import SHOP_CATALOG
from app.models.gamification import ShopItem


async def seed_shop_items(
    session,
    catalog: Sequence[dict[str, Any]] = SHOP_CATALOG,
) -> tuple[int, int]:
    """Upsert the canonical local shop catalog and return (created, updated)."""
    total_seeded = 0
    total_updated = 0

    for item in catalog:
        # Check if item already exists by name
        stmt = select(ShopItem).where(ShopItem.name == item["name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            # Update existing item
            existing.description = item["description"]
            existing.item_type = item["item_type"]
            existing.price_gems = item["price_gems"]
            existing.icon_url = item.get("icon_url")
            existing.effects = item.get("effects")
            existing.is_available = item.get("is_available", True)
            total_updated += 1
        else:
            # Create new item
            db_item = ShopItem(
                id=uuid.uuid4(),
                name=item["name"],
                description=item["description"],
                item_type=item["item_type"],
                price_gems=item["price_gems"],
                icon_url=item.get("icon_url"),
                effects=item.get("effects"),
                is_available=item.get("is_available", True),
                created_at=datetime.now(UTC),
            )
            session.add(db_item)
            total_seeded += 1

    await session.commit()
    return total_seeded, total_updated


async def main():
    async with AsyncSessionLocal() as session:
        print("=== Seeding Shop Items ===")
        total_seeded, total_updated = await seed_shop_items(session)
        print(f"Shop items: Seeded {total_seeded}, Updated {total_updated}")


if __name__ == "__main__":
    asyncio.run(main())
