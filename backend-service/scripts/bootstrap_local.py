#!/usr/bin/env python3
# ruff: noqa: E402
"""Safely initialise or upgrade the configured local database.

This command never drops schemas, tables, volumes, or data. It accepts only an
empty database or one already managed by Alembic; an unversioned populated
database is reported and left unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401  # Register every model before Base.metadata is used.
from app.core.bootstrap import BootstrapSafetyError, bootstrap_database, inspect_bootstrap_state
from app.core.database import engine


async def _run_alembic(action: str) -> None:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        action,
        "head",
        cwd=str(BACKEND_ROOT),
    )
    return_code = await process.wait()
    if return_code:
        raise RuntimeError(f"alembic {action} head failed with exit code {return_code}")


async def main(check_only: bool) -> int:
    try:
        if check_only:
            state = await inspect_bootstrap_state(engine)
            print(f"Database state: {state.value}")
            return 0

        result = await bootstrap_database(engine, _run_alembic)
        print(f"Bootstrap complete: {result.action}.")
        return 0
    except BootstrapSafetyError as exc:
        print(f"Bootstrap stopped safely: {exc}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report database state without changing it",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.check)))
