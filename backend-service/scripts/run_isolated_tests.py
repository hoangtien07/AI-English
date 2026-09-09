"""Run the backend pytest suite against a one-run PostgreSQL database.

Run from ``backend-service`` with ``python -m scripts.run_isolated_tests``.
The runner reads only the PostgreSQL credentials from the repository-root
``.env`` used by local Compose.  It deliberately never prints those values.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import asyncpg
from dotenv import dotenv_values

COMPOSE_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
BACKEND_SERVICE_ROOT = Path(__file__).resolve().parents[1]
PYTEST_TEMP_ROOT = BACKEND_SERVICE_ROOT / ".pytest-tmp"
DATABASE_NAME_PATTERN = re.compile(r"^lexilingo_pytest_[0-9a-f]{32}_test$")


@dataclass(frozen=True)
class ComposePostgresConfig:
    """Credentials and endpoint exposed by the local Compose PostgreSQL service."""

    user: str
    password: str = field(repr=False)
    app_database: str = "lexilingo"
    host: str = "127.0.0.1"
    port: int = 5432


def load_compose_postgres_config(env_file: Path = COMPOSE_ENV_FILE) -> ComposePostgresConfig:
    """Load the database access values needed for local Compose, without logging them."""
    if not env_file.is_file():
        raise RuntimeError(f"Local Compose environment file is missing: {env_file}")

    values = dotenv_values(env_file)
    user = values.get("POSTGRES_USER") or "lexilingo"
    password = values.get("POSTGRES_PASSWORD")
    app_database = values.get("POSTGRES_DB") or "lexilingo"
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD must be set in the local Compose .env")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", user):
        raise RuntimeError("POSTGRES_USER contains unsupported PostgreSQL identifier characters")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", app_database):
        raise RuntimeError("POSTGRES_DB contains unsupported PostgreSQL identifier characters")

    return ComposePostgresConfig(user=user, password=password, app_database=app_database)


def new_test_database_name() -> str:
    """Return a PostgreSQL-safe name that can never be the Compose application DB."""
    return f"lexilingo_pytest_{uuid.uuid4().hex}_test"


def _quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def _database_url(config: ComposePostgresConfig, database: str) -> str:
    """Build the async SQLAlchemy URL without ever displaying it."""
    from urllib.parse import quote

    return (
        f"postgresql+asyncpg://{quote(config.user, safe='')}:{quote(config.password, safe='')}"
        f"@{config.host}:{config.port}/{database}"
    )


async def _connect(config: ComposePostgresConfig) -> asyncpg.Connection:
    return await asyncpg.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database="postgres",
    )


async def create_owned_test_database(config: ComposePostgresConfig, database: str) -> None:
    """Create one new isolated database, refusing any unexpected name or collision."""
    if not DATABASE_NAME_PATTERN.fullmatch(database):
        raise RuntimeError(
            "Refusing to create a database outside the isolated pytest naming scheme"
        )
    if database == config.app_database:
        raise RuntimeError("Refusing to use the Compose application database for tests")

    connection = await _connect(config)
    try:
        exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", database)
        if exists:
            raise RuntimeError(
                "Generated isolated test database name already exists; retry the command"
            )
        await connection.execute(f"CREATE DATABASE {_quote_identifier(database)}")
    finally:
        await connection.close()


async def drop_owned_test_database(config: ComposePostgresConfig, database: str) -> None:
    """Drop only the database whose exact generated name this runner created."""
    if not DATABASE_NAME_PATTERN.fullmatch(database):
        raise RuntimeError("Refusing to drop a database outside the isolated pytest naming scheme")
    if database == config.app_database:
        raise RuntimeError("Refusing to drop the Compose application database")

    connection = await _connect(config)
    try:
        await connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            database,
        )
        await connection.execute(f"DROP DATABASE {_quote_identifier(database)}")
    finally:
        await connection.close()


def _pytest_environment(config: ComposePostgresConfig, database: str) -> dict[str, str]:
    environment = os.environ.copy()
    database_url = _database_url(config, database)
    environment.update(
        {
            "APP_ENV": "testing",
            "DEBUG": "false",
            "DATABASE_URL": database_url,
            "TEST_DATABASE_URL": database_url,
        }
    )
    return environment


def run_pytest(
    config: ComposePostgresConfig, database: str, pytest_args: list[str], base_temp: Path
) -> int:
    """Run the broad backend suite while keeping generated credentials out of stdout."""
    command = [sys.executable, "-m", "pytest", "tests", "--basetemp", str(base_temp), *pytest_args]
    return subprocess.run(
        command, env=_pytest_environment(config, database), check=False
    ).returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest against a temporary isolated Compose DB"
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to pytest (prefix them with --, for example: -- -x)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    pytest_args = args.pytest_args[1:] if args.pytest_args[:1] == ["--"] else args.pytest_args
    database: str | None = None
    base_temp: Path | None = None
    temp_root_created = False
    created = False
    test_status = 1
    cleanup_failed = False

    try:
        config = load_compose_postgres_config()
        database = new_test_database_name()
        asyncio.run(create_owned_test_database(config, database))
        created = True
        temp_root_created = not PYTEST_TEMP_ROOT.exists()
        PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        base_temp = Path(tempfile.mkdtemp(prefix="isolated-run-", dir=PYTEST_TEMP_ROOT))
        print("Created an isolated PostgreSQL test database; running backend pytest suite.")
        test_status = run_pytest(config, database, pytest_args, base_temp)
    except KeyboardInterrupt:
        print(
            "Backend pytest interrupted; cleaning up the isolated test database.", file=sys.stderr
        )
        test_status = 130
    except Exception:
        print(
            "Unable to create or run against the isolated local Compose test database. "
            "Ensure the local PostgreSQL service is running and its credentials permit CREATEDB.",
            file=sys.stderr,
        )
        test_status = 2
    finally:
        if base_temp is not None:
            shutil.rmtree(base_temp, ignore_errors=True)
        if temp_root_created:
            try:
                PYTEST_TEMP_ROOT.rmdir()
            except OSError:
                pass
        if created and database is not None:
            try:
                asyncio.run(drop_owned_test_database(config, database))
                print("Removed the isolated PostgreSQL test database created by this run.")
            except Exception:
                cleanup_failed = True
                print(
                    "Could not remove the isolated test database created by this run; "
                    "manual cleanup is required.",
                    file=sys.stderr,
                )

    return 2 if cleanup_failed else test_status


if __name__ == "__main__":
    raise SystemExit(main())
