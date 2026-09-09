"""Safe, deterministic database bootstrap primitives for local environments."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine


class BootstrapState(StrEnum):
    FRESH = "fresh"
    VERSIONED = "versioned"
    UNVERSIONED = "unversioned"


class BootstrapSafetyError(RuntimeError):
    """Raised before touching an existing database without Alembic history."""


@dataclass(frozen=True)
class BootstrapResult:
    state: BootstrapState
    action: str


MigrationRunner = Callable[[str], Awaitable[None]]


async def inspect_bootstrap_state(engine: AsyncEngine) -> BootstrapState:
    """Classify a database without changing it."""
    async with engine.connect() as connection:
        table_names = await connection.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
        non_alembic_tables = [name for name in table_names if name != "alembic_version"]

        if "alembic_version" in table_names:
            version = await connection.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            if version is not None:
                return BootstrapState.VERSIONED
            if non_alembic_tables:
                return BootstrapState.UNVERSIONED
            return BootstrapState.FRESH

    if non_alembic_tables:
        return BootstrapState.UNVERSIONED
    return BootstrapState.FRESH


async def bootstrap_database(
    engine: AsyncEngine,
    run_migration: MigrationRunner,
) -> BootstrapResult:
    """Upgrade an empty or Alembic-managed database using migrations only.

    This deliberately refuses an unversioned database that already contains
    tables.  Stamping that database at ``head`` could hide an incomplete schema
    and is less safe than stopping for an explicit operator decision.
    """
    state = await inspect_bootstrap_state(engine)
    if state is BootstrapState.FRESH:
        await run_migration("upgrade")
        return BootstrapResult(state=state, action="upgraded empty database to Alembic head")

    if state is BootstrapState.VERSIONED:
        await run_migration("upgrade")
        return BootstrapResult(state=state, action="upgraded Alembic schema to head")

    raise BootstrapSafetyError(
        "Database contains tables but has no alembic_version table; refusing to stamp or "
        "alter it automatically. Back it up and reconcile its schema before adoption."
    )
