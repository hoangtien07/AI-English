"""Inspect a user's level/rank and leaderboard entries.

Usage:
    python3 scripts/inspect_users.py --email user@example.com [--pattern %name%]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend-service to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.core.database import engine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Email of the user to inspect")
    parser.add_argument(
        "--pattern",
        help="Optional LIKE pattern also matched against display_name and username",
    )
    return parser.parse_args()


async def check_users() -> None:
    args = _parse_args()
    email = args.email.strip().lower()
    pattern = args.pattern or email

    async with engine.begin() as conn:
        print("=== MATCHING USERS ===")
        res = await conn.execute(
            text("""
            SELECT id, email, username, display_name, level, numeric_level, rank, rank_score, total_xp
            FROM users
            WHERE email = :email OR display_name LIKE :pattern OR username LIKE :pattern
        """),
            {"email": email, "pattern": pattern},
        )
        users = res.fetchall()
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Name: {u.display_name} | Lvl: {u.level} | NumLvl: {u.numeric_level} | Rank: {u.rank} | XP: {u.total_xp}")

        print("\n=== MATCHING LEADERBOARD ENTRIES ===")
        res_l = await conn.execute(
            text("""
            SELECT id, user_id, league, week_start, xp_earned
            FROM leaderboard_entries
            WHERE user_id IN (
                SELECT id FROM users
                WHERE email = :email OR display_name LIKE :pattern OR username LIKE :pattern
            )
        """),
            {"email": email, "pattern": pattern},
        )
        entries = res_l.fetchall()
        for e in entries:
            uname = next((u.email for u in users if u.id == e.user_id), "Unknown")
            print(f"User: {uname} | League: {e.league} | Week: {e.week_start} | XP: {e.xp_earned}")


if __name__ == "__main__":
    asyncio.run(check_users())
