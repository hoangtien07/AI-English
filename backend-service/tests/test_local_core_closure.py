"""Local-core closure regressions that require no SMTP, Docker volume, or live service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, Integer, MetaData, String, Table, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.bootstrap import (
    BootstrapSafetyError,
    BootstrapState,
    bootstrap_database,
    inspect_bootstrap_state,
)
from app.core.database import Base, get_db
from app.models.gamification import ShopItem
from app.models.progress import Streak
from app.models.rbac import Role
from app.models.user import RefreshToken, User
from app.services.starter_reward_service import StarterRewardService
from scripts.seed_shop_items import seed_shop_items


def _sqlite_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


@pytest.mark.asyncio
async def test_bootstrap_handles_fresh_and_existing_versioned_database(tmp_path: Path):
    """Fresh bootstrap migrates once; the next run upgrades without losing a row."""
    engine = create_async_engine(_sqlite_url(tmp_path / "bootstrap.sqlite3"))
    metadata = MetaData()
    catalog = Table(
        "catalog",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
    )
    actions: list[str] = []

    async def migration_runner(action: str) -> None:
        actions.append(action)
        if action == "upgrade":
            async with engine.begin() as connection:
                await connection.run_sync(metadata.create_all)
                await connection.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"
                    )
                )
                if not await connection.scalar(text("SELECT COUNT(*) FROM alembic_version")):
                    await connection.execute(
                        text("INSERT INTO alembic_version (version_num) VALUES ('head')")
                    )

    try:
        first = await bootstrap_database(engine, migration_runner)
        assert first.state is BootstrapState.FRESH
        assert actions == ["upgrade"]

        async with engine.begin() as connection:
            await connection.execute(catalog.insert().values(id=1, name="retained"))

        second = await bootstrap_database(engine, migration_runner)
        assert second.state is BootstrapState.VERSIONED
        assert actions == ["upgrade", "upgrade"]

        async with engine.connect() as connection:
            assert (await connection.scalar(select(func.count()).select_from(catalog))) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_refuses_populated_unversioned_database(tmp_path: Path):
    """A legacy database is detected but never adopted or modified implicitly."""
    engine = create_async_engine(_sqlite_url(tmp_path / "legacy.sqlite3"))
    metadata = MetaData()
    Table("legacy_data", metadata, Column("id", Integer, primary_key=True))
    calls: list[str] = []

    async def migration_runner(action: str) -> None:
        calls.append(action)

    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE TABLE legacy_data (id INTEGER PRIMARY KEY)"))
            await connection.execute(text("INSERT INTO legacy_data (id) VALUES (1)"))
            await connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )

        assert await inspect_bootstrap_state(engine) is BootstrapState.UNVERSIONED
        with pytest.raises(BootstrapSafetyError, match="refusing"):
            await bootstrap_database(engine, migration_runner)
        assert calls == []

        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT COUNT(*) FROM legacy_data")) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_shop_catalog_seed_is_idempotent(tmp_path: Path):
    """The selected minimal local seed creates rows once and then only updates them."""
    engine = create_async_engine(_sqlite_url(tmp_path / "seed.sqlite3"))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    catalog = (
        {
            "name": "Local Test Hint",
            "description": "A deterministic local seed fixture.",
            "item_type": "hint_pack",
            "price_gems": 15,
            "effects": {"hints": 1},
        },
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(ShopItem.__table__.create)

        async with session_factory() as session:
            assert await seed_shop_items(session, catalog) == (1, 0)
        async with session_factory() as session:
            assert await seed_shop_items(session, catalog) == (0, 1)
            assert await session.scalar(select(func.count(ShopItem.id))) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_local_auth_lifecycle_without_smtp_or_live_apis(tmp_path: Path):
    """Exercise local register, verification, login, me, refresh, and logout end-to-end."""
    from app.core.token_blacklist import TokenBlacklist
    from app.main import app

    engine = create_async_engine(_sqlite_url(tmp_path / "auth.sqlite3"))
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    sent_email = AsyncMock()
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[Role.__table__, User.__table__, RefreshToken.__table__],
                )
            )

        transport = ASGITransport(app=app)
        with (
            patch.object(
                StarterRewardService,
                "grant_new_user_reward",
                new=AsyncMock(),
            ),
            patch(
                "app.routes.auth.EmailService.send_verification_email",
                new=sent_email,
            ),
            patch.object(TokenBlacklist, "add", new=AsyncMock()),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                register = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "local.lifecycle@example.com",
                        "username": "local_lifecycle",
                        "password": "SecurePass123!",
                    },
                )
                assert register.status_code == 201
                assert sent_email.await_count == 1

                blocked_login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "local.lifecycle@example.com", "password": "SecurePass123!"},
                )
                assert blocked_login.status_code == 403

                verification = await client.post(
                    "/api/v1/auth/verify-email",
                    json={"token": sent_email.await_args.kwargs["token"]},
                )
                assert verification.status_code == 200
                assert verification.json()["verified"] is True

                login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "local.lifecycle@example.com", "password": "SecurePass123!"},
                )
                assert login.status_code == 200
                tokens = login.json()

                me = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                assert me.status_code == 200
                assert me.json()["email"] == "local.lifecycle@example.com"

                refreshed = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": tokens["refresh_token"]},
                )
                assert refreshed.status_code == 200
                rotated = refreshed.json()

                logout = await client.post(
                    "/api/v1/auth/logout",
                    json={"refresh_token": rotated["refresh_token"]},
                    headers={"Authorization": f"Bearer {rotated['access_token']}"},
                )
                assert logout.status_code == 200

                revoked_refresh = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": rotated["refresh_token"]},
                )
                assert revoked_refresh.status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_user_and_progress_survive_a_new_database_connection(tmp_path: Path):
    """Representative learner data remains after an engine/pool restart without reset."""
    database_url = _sqlite_url(tmp_path / "persistence.sqlite3")
    first_engine = create_async_engine(database_url)
    first_sessions = async_sessionmaker(first_engine, expire_on_commit=False)
    try:
        async with first_engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(
                    sync_connection,
                    tables=[User.__table__, Streak.__table__],
                )
            )
        async with first_sessions() as session:
            user = User(
                email="persisted@example.com",
                username="persisted_user",
                hashed_password="not-used-by-this-persistence-test",
                is_verified=True,
            )
            session.add(user)
            await session.flush()
            session.add(Streak(user_id=user.id, current_streak=7, longest_streak=9))
            await session.commit()
    finally:
        await first_engine.dispose()

    restarted_engine = create_async_engine(database_url)
    restarted_sessions = async_sessionmaker(restarted_engine, expire_on_commit=False)
    try:
        async with restarted_sessions() as session:
            persisted_user = await session.scalar(
                select(User).where(User.email == "persisted@example.com")
            )
            assert persisted_user is not None
            persisted_streak = await session.scalar(
                select(Streak).where(Streak.user_id == persisted_user.id)
            )
            assert persisted_streak.current_streak == 7
            assert persisted_streak.longest_streak == 9
    finally:
        await restarted_engine.dispose()
