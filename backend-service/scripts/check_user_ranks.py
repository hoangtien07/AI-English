"""Inspect (and optionally max out) a user's level/rank/gems.

Usage:
    python3 scripts/check_user_ranks.py --email user@example.com
    python3 scripts/check_user_ranks.py --email user@example.com --apply
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend-service to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.core.database import engine

from app.services.rank_service import calculate_rank


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Email of the user to inspect")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually set the user to MAX stats (C2, level 100, 200000 XP, 9999 gems). "
        "Without this flag the script only prints current stats.",
    )
    return parser.parse_args()


async def check_users() -> None:
    args = _parse_args()
    email = args.email.strip().lower()

    async with engine.begin() as conn:
        res = await conn.execute(
            text("""
            SELECT id, email, username, display_name, level, numeric_level, rank, rank_score, total_xp
            FROM users WHERE email = :email
        """),
            {"email": email},
        )
        user = res.fetchone()
        if not user:
            print(f"No user with email '{email}' found in database.")
            return

        print(
            f"[INFO] {email}: Level={user.level}, NumLvl={user.numeric_level}, "
            f"Rank={user.rank}, Score={user.rank_score}, XP={user.total_xp}"
        )
        if not args.apply:
            print("Dry run only — pass --apply to set MAX stats.")
            return

        print(f"[ACTION] Syncing {email} to MAX stats (C2, level 100, 200000 XP, 9999 gems)...")

        new_level = "C2"
        new_numeric_level = 100
        new_xp = 200000
        rank_info = calculate_rank(new_numeric_level, new_level)

        await conn.execute(
            text("""
                UPDATE users
                SET level = :level,
                    numeric_level = :numeric_level,
                    total_xp = :total_xp,
                    rank = :rank,
                    rank_score = :rank_score,
                    rank_level_score = :rank_level_score,
                    rank_proficiency_score = :rank_proficiency_score
                WHERE id = :user_id
            """),
            {
                "level": new_level,
                "numeric_level": new_numeric_level,
                "total_xp": new_xp,
                "rank": rank_info.rank.value,
                "rank_score": rank_info.score,
                "rank_level_score": rank_info.level_score,
                "rank_proficiency_score": rank_info.proficiency_score,
                "user_id": user.id,
            },
        )

        # Clear and create UserProficiencyProfile
        await conn.execute(
            text("DELETE FROM user_proficiency_profiles WHERE user_id = :user_id"),
            {"user_id": user.id},
        )
        await conn.execute(
            text("""
                INSERT INTO user_proficiency_profiles (id, user_id, assessed_level, total_xp, overall_score, total_exercises_completed, total_correct_exercises, created_at, updated_at)
                VALUES (:id, :user_id, :assessed_level, :total_xp, :overall_score, :total_exercises_completed, :total_correct_exercises, NOW(), NOW())
            """),
            {
                "id": os.urandom(16).hex(),
                "user_id": user.id,
                "assessed_level": new_level,
                "total_xp": new_xp,
                "overall_score": 100.0,
                "total_exercises_completed": 1000,
                "total_correct_exercises": 1000,
            },
        )

        # Clear / Create / Update Wallet for 9999 gems
        await conn.execute(
            text("DELETE FROM user_wallets WHERE user_id = :user_id"),
            {"user_id": user.id},
        )
        await conn.execute(
            text("""
                INSERT INTO user_wallets (id, user_id, gems, total_gems_earned, total_gems_spent, created_at, updated_at)
                VALUES (:id, :user_id, 9999, 9999, 0, NOW(), NOW())
            """),
            {
                "id": os.urandom(16).hex(),
                "user_id": user.id,
            },
        )

        # Verify update
        res_verify = await conn.execute(
            text("""
                SELECT level, numeric_level, rank, rank_score, total_xp
                FROM users WHERE id = :user_id
            """),
            {"user_id": user.id},
        )
        updated = res_verify.fetchone()

        res_wallet = await conn.execute(
            text("""
                SELECT gems FROM user_wallets WHERE user_id = :user_id
            """),
            {"user_id": user.id},
        )
        wallet_gems = res_wallet.scalar()

        print(
            f"[INFO] {email} (AFTER): Level={updated.level}, NumLvl={updated.numeric_level}, "
            f"Rank={updated.rank}, Score={updated.rank_score}, XP={updated.total_xp}, Gems={wallet_gems}"
        )


if __name__ == "__main__":
    asyncio.run(check_users())
