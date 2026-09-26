"""
Setup an Admin User with Google OAuth Support

Creates or updates a single admin user to support Google OAuth login.

Usage:
    python3 scripts/setup_admin_oauth.py --email you@example.com \
        [--role admin|super_admin] [--username name] [--display-name "Name"]

Run this script after seeding roles and permissions.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.rbac import Role


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Email of the admin user to create or update")
    parser.add_argument(
        "--role",
        choices=["admin", "super_admin"],
        default="admin",
        help="Role to assign (default: admin)",
    )
    parser.add_argument("--username", help="Username (default: email local part)")
    parser.add_argument("--display-name", help="Display name (default: role name)")
    return parser.parse_args()


async def setup_admin_oauth() -> None:
    args = _parse_args()
    email = args.email.strip().lower()
    username = (args.username or email.split("@")[0]).strip()
    display_name = (args.display_name or args.role.replace("_", " ").title()).strip()

    async with AsyncSessionLocal() as db:
        print(" Setting up admin user with Google OAuth...")

        result = await db.execute(select(Role).where(Role.slug == args.role))
        role = result.scalar_one_or_none()
        if not role:
            print(f" Error: role '{args.role}' not found. Run Alembic migrations and seed roles first.")
            return
        print(f"  Found role: {role.slug} (ID: {role.id})")

        import bcrypt
        oauth_password_hash = bcrypt.hashpw(b"OAUTH_USER_NO_PASSWORD", bcrypt.gensalt(12)).decode()

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            old_role_id = user.role_id
            user.add_provider("google")
            # Only reset password to placeholder if user has no local credentials.
            # Multi-provider accounts keep their real local password intact.
            if not user.has_local_auth:
                user.hashed_password = oauth_password_hash
            user.role_id = role.id
            user.display_name = display_name
            user.is_verified = True
            user.is_active = True

            print(f"\n   Updated user: {email}")
            print(f"     - Providers: {user.provider}")
            print(f"     - Role: {args.role}")
            if old_role_id != user.role_id:
                print(f"     - Role ID changed: {old_role_id} → {user.role_id}")
        else:
            base_username = username
            counter = 1
            while True:
                result = await db.execute(
                    select(User).where(User.username == username)
                )
                if not result.scalar_one_or_none():
                    break
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                hashed_password=oauth_password_hash,
                display_name=display_name,
                provider=["google"],
                role_id=role.id,
                is_verified=True,
                is_active=True,
                level="A1",
            )
            db.add(user)

            print(f"\n   Created user: {email}")
            print(f"     - Username: {username}")
            print("     - Provider: google")
            print(f"     - Role: {args.role}")

        await db.commit()
        print("\n Admin OAuth setup completed!")
        print("\n Next steps:")
        print("   1. Make sure GOOGLE_CLIENT_ID and GOOGLE_ADMIN_CLIENT_ID are set in backend .env")
        print("   2. Test Google OAuth login at /auth/google endpoint with source='admin'")


if __name__ == "__main__":
    asyncio.run(setup_admin_oauth())
