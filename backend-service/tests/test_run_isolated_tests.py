"""Safety tests for the isolated local-Compose PostgreSQL test runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts import run_isolated_tests as runner


def test_load_compose_postgres_config_reads_only_required_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_USER=local_user\nPOSTGRES_PASSWORD=not-printed\nPOSTGRES_DB=local_app\n",
        encoding="utf-8",
    )

    config = runner.load_compose_postgres_config(env_file)

    assert config.user == "local_user"
    assert config.password == "not-printed"
    assert config.app_database == "local_app"
    assert "not-printed" not in repr(config)


def test_new_test_database_name_is_unique_and_never_an_application_name():
    database = runner.new_test_database_name()

    assert runner.DATABASE_NAME_PATTERN.fullmatch(database)
    assert database != "lexilingo"


@pytest.mark.asyncio
async def test_create_owned_test_database_refuses_non_generated_name_before_connecting():
    config = runner.ComposePostgresConfig(user="tester", password="secret")

    with patch.object(runner, "_connect", new=AsyncMock()) as connect:
        with pytest.raises(RuntimeError, match="Refusing to create"):
            await runner.create_owned_test_database(config, "lexilingo")

    connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_and_cleanup_only_target_the_generated_database():
    database = "lexilingo_pytest_0123456789abcdef0123456789abcdef_test"
    connection = AsyncMock()
    connection.fetchval.return_value = None
    config = runner.ComposePostgresConfig(user="tester", password="secret")

    with patch.object(runner, "_connect", new=AsyncMock(return_value=connection)):
        await runner.create_owned_test_database(config, database)
        await runner.drop_owned_test_database(config, database)

    statements = [call.args[0] for call in connection.execute.await_args_list]
    assert f'CREATE DATABASE "{database}"' in statements
    assert f'DROP DATABASE "{database}"' in statements
    assert all('lexilingo"' not in statement for statement in statements)


def test_pytest_environment_uses_the_generated_database_without_exposing_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://do-not-use")
    config = runner.ComposePostgresConfig(user="tester", password="secret value")
    database = "lexilingo_pytest_0123456789abcdef0123456789abcdef_test"

    environment = runner._pytest_environment(config, database)

    assert environment["DATABASE_URL"] == environment["TEST_DATABASE_URL"]
    assert environment["DATABASE_URL"].endswith(f"/{database}")
    assert environment["APP_ENV"] == "testing"


def test_run_pytest_uses_the_owned_base_temp_directory(tmp_path: Path):
    config = runner.ComposePostgresConfig(user="tester", password="secret")
    database = "lexilingo_pytest_0123456789abcdef0123456789abcdef_test"
    base_temp = tmp_path / "isolated-run-owned"

    with patch.object(
        runner.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()
    ) as run:
        assert runner.run_pytest(config, database, ["-q"], base_temp) == 0

    command = run.call_args.args[0]
    assert command[3:6] == ["tests", "--basetemp", str(base_temp)]
