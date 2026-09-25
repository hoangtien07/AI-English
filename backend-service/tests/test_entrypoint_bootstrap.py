import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "entrypoint.sh"


def _has_working_bash() -> bool:
    """The deployment entrypoint is Bash; Windows' WSL launcher is not Bash."""
    try:
        return (
            subprocess.run(
                ["bash", "-c", ":"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _has_working_bash(), reason="requires a functioning POSIX Bash runtime"
)


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source)
    path.chmod(0o755)


def test_fresh_database_bootstrap_uses_migrations_and_redacts_database_url(
    tmp_path,
):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    command_log = tmp_path / "commands.log"
    _write_executable(
        fake_bin / "python",
        """#!/usr/bin/env bash
if [ "${1:-}" = "-" ]; then
  cat >/dev/null
  echo fresh
else
  printf 'python %s\n' "$*" >> "$COMMAND_LOG"
fi
""",
    )
    _write_executable(
        fake_bin / "alembic",
        """#!/usr/bin/env bash
printf 'alembic %s\n' "$*" >> "$COMMAND_LOG"
""",
    )
    _write_executable(
        fake_bin / "uvicorn",
        """#!/usr/bin/env bash
printf 'uvicorn %s\n' "$*" >> "$COMMAND_LOG"
""",
    )
    secret_url = "postgresql+asyncpg://private-user:super-secret@db.internal/app"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "COMMAND_LOG": str(command_log),
        "DATABASE_URL": secret_url,
    }

    result = subprocess.run(
        ["bash", str(ENTRYPOINT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    output = result.stdout + result.stderr
    commands = command_log.read_text().splitlines()
    assert secret_url not in output
    assert "private-user" not in output
    assert "super-secret" not in output
    assert "DATABASE_URL: <configured>" in output
    assert commands[:1] == ["alembic upgrade head"]
    assert commands[1].startswith("uvicorn app.main:app")


def test_unreachable_probe_redacts_secret_exception_and_still_starts_api(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    command_log = tmp_path / "commands.log"
    _write_executable(
        fake_bin / "python",
        """#!/usr/bin/env bash
if [ "${1:-}" = "-" ]; then
  cat >/dev/null
  echo 'DB check error: InvalidPasswordError' >&2
  echo unreachable
fi
""",
    )
    _write_executable(
        fake_bin / "uvicorn",
        """#!/usr/bin/env bash
printf 'uvicorn %s\n' "$*" >> "$COMMAND_LOG"
""",
    )
    secret_url = "postgresql+asyncpg://secret-user:secret-password@db.internal/app_test"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "COMMAND_LOG": str(command_log),
        "DATABASE_URL": secret_url,
    }

    result = subprocess.run(
        ["bash", str(ENTRYPOINT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    output = result.stdout + result.stderr
    assert "DB check error: InvalidPasswordError" in output
    assert "Database unreachable during startup probe" in output
    assert secret_url not in output
    assert "secret-user" not in output
    assert "secret-password" not in output
    assert command_log.read_text().startswith("uvicorn app.main:app")


def test_probe_source_logs_exception_type_not_exception_message():
    source = ENTRYPOINT.read_text()

    assert "type(e).__name__" in source
    assert 'f"DB check error: {e}"' not in source
