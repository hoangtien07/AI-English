from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, exc, text

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c4e6a8f1b2d3_add_content_agent_import_identity.py"
)
spec = importlib.util.spec_from_file_location(
    "c4e6a8f1b2d3_add_content_agent_import_identity", MIGRATION_PATH
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_metadata() -> None:
    assert migration.revision == "c4e6a8f1b2d3"
    assert migration.down_revision == "4a7b1c9e2d30"
    assert migration.branch_labels is None
    assert migration.depends_on is None


def test_migration_upgrade_downgrade_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple, dict]] = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda *args, **kwargs: calls.append(("add_column", args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda *args, **kwargs: calls.append(("create_index", args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_index",
        lambda *args, **kwargs: calls.append(("drop_index", args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_column",
        lambda *args, **kwargs: calls.append(("drop_column", args, kwargs)),
    )

    migration.upgrade()

    assert len(calls) == 2
    add_call, idx_call = calls[0], calls[1]

    assert add_call[0] == "add_column"
    assert add_call[1][0] == "content_agent_jobs"
    col = add_call[1][1]
    assert isinstance(col, sa.Column)
    assert col.name == "import_identity"
    assert isinstance(col.type, sa.String)
    assert col.type.length == 64
    assert col.nullable is True

    assert idx_call[0] == "create_index"
    assert idx_call[1][0] == "uq_content_agent_jobs_import_identity"
    assert idx_call[1][1] == "content_agent_jobs"
    assert idx_call[1][2] == ["import_identity"]
    assert idx_call[2].get("unique") is True

    calls.clear()
    migration.downgrade()

    assert len(calls) == 2
    drop_idx_call, drop_col_call = calls[0], calls[1]

    assert drop_idx_call[0] == "drop_index"
    assert drop_idx_call[1][0] == "uq_content_agent_jobs_import_identity"
    assert drop_idx_call[2].get("table_name") == "content_agent_jobs"

    assert drop_col_call[0] == "drop_column"
    assert drop_col_call[1][0] == "content_agent_jobs"
    assert drop_col_call[1][1] == "import_identity"


def test_migration_sqlite_upgrade_downgrade_and_uniqueness() -> None:
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        # Create pre-migration table mimicking legacy schema
        conn.execute(
            text(
                "CREATE TABLE content_agent_jobs ("
                "  id VARCHAR(36) PRIMARY KEY,"
                "  status VARCHAR(32) NOT NULL,"
                "  request_hash VARCHAR(64) NOT NULL"
                ")"
            )
        )
        # Pre-populate legacy rows
        conn.execute(
            text(
                "INSERT INTO content_agent_jobs (id, status, request_hash) "
                "VALUES ('leg-1', 'completed', 'h1'), ('leg-2', 'failed', 'h2')"
            )
        )
        conn.commit()

        # Configure migration context
        ctx = MigrationContext.configure(conn)
        orig_proxy = getattr(migration.op, "_proxy", None)
        migration.op._proxy = Operations(ctx)

        try:
            # Run upgrade
            migration.upgrade()
            conn.commit()

            # Verify column exists and is nullable
            table_info = conn.execute(
                text("PRAGMA table_info(content_agent_jobs)")
            ).fetchall()
            col_names = [row[1] for row in table_info]
            assert "import_identity" in col_names
            col_row = next(r for r in table_info if r[1] == "import_identity")
            assert col_row[3] == 0  # notnull == 0 means nullable

            # Verify unique index exists
            index_list = conn.execute(
                text("PRAGMA index_list(content_agent_jobs)")
            ).fetchall()
            idx_names = [row[1] for row in index_list]
            assert "uq_content_agent_jobs_import_identity" in idx_names
            idx_row = next(
                r for r in index_list if r[1] == "uq_content_agent_jobs_import_identity"
            )
            assert idx_row[2] == 1  # unique == 1

            # Verify existing legacy rows now have import_identity = NULL
            legacy_vals = conn.execute(
                text("SELECT id, import_identity FROM content_agent_jobs WHERE id IN ('leg-1', 'leg-2')")
            ).fetchall()
            assert all(row[1] is None for row in legacy_vals)

            # Insert first non-null import identity
            identity = "a" * 64
            conn.execute(
                text(
                    "INSERT INTO content_agent_jobs (id, status, request_hash, import_identity) "
                    f"VALUES ('job-1', 'queued', 'h3', '{identity}')"
                )
            )
            conn.commit()

            # Inserting duplicate non-null import identity must fail unique constraint
            with pytest.raises(exc.IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO content_agent_jobs (id, status, request_hash, import_identity) "
                        f"VALUES ('job-2', 'queued', 'h4', '{identity}')"
                    )
                )
            conn.rollback()

            # Inserting multiple rows with import_identity = NULL succeeds (nullable compatibility)
            conn.execute(
                text(
                    "INSERT INTO content_agent_jobs (id, status, request_hash, import_identity) "
                    "VALUES ('job-null-1', 'queued', 'h5', NULL)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO content_agent_jobs (id, status, request_hash, import_identity) "
                    "VALUES ('job-null-2', 'queued', 'h6', NULL)"
                )
            )
            conn.commit()

            # Run downgrade
            migration.downgrade()
            conn.commit()

            # Verify column and index are dropped
            table_info_after = conn.execute(
                text("PRAGMA table_info(content_agent_jobs)")
            ).fetchall()
            col_names_after = [row[1] for row in table_info_after]
            assert "import_identity" not in col_names_after

            index_list_after = conn.execute(
                text("PRAGMA index_list(content_agent_jobs)")
            ).fetchall()
            idx_names_after = [row[1] for row in index_list_after]
            assert "uq_content_agent_jobs_import_identity" not in idx_names_after
        finally:
            migration.op._proxy = orig_proxy

    engine.dispose()
