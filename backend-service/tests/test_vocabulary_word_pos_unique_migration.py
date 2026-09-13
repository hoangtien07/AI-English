from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "e1a2b3c4d5f6_add_vocabulary_word_pos_unique.py"
)
spec = importlib.util.spec_from_file_location(
    "e1a2b3c4d5f6_add_vocabulary_word_pos_unique", MIGRATION_PATH
)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_migration_metadata() -> None:
    assert migration.revision == "e1a2b3c4d5f6"
    assert migration.down_revision == "c4e6a8f1b2d3"
    assert migration.branch_labels is None
    assert migration.depends_on is None


def test_upgrade_and_downgrade_target_exact_vocabulary_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple, dict]] = []
    monkeypatch.setattr(
        migration.op,
        "create_unique_constraint",
        lambda *args, **kwargs: calls.append(("create_unique_constraint", args, kwargs)),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda *args, **kwargs: calls.append(("drop_constraint", args, kwargs)),
    )

    migration.upgrade()
    migration.downgrade()

    assert calls == [
        (
            "create_unique_constraint",
            ("uq_vocab_word_pos", "vocabulary_items", ["word", "part_of_speech"]),
            {},
        ),
        (
            "drop_constraint",
            ("uq_vocab_word_pos", "vocabulary_items"),
            {"type_": "unique"},
        ),
    ]


def test_postgresql_upgrade_and_downgrade_render_unique_constraint_sql() -> None:
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    original_proxy = getattr(migration.op, "_proxy", None)
    migration.op._proxy = Operations(context)
    try:
        migration.upgrade()
        upgrade_sql = output.getvalue()
        output.seek(0)
        output.truncate(0)

        migration.downgrade()
        downgrade_sql = output.getvalue()
    finally:
        migration.op._proxy = original_proxy

    assert "ALTER TABLE vocabulary_items ADD CONSTRAINT uq_vocab_word_pos UNIQUE (word, part_of_speech);" in upgrade_sql
    assert "ALTER TABLE vocabulary_items DROP CONSTRAINT uq_vocab_word_pos;" in downgrade_sql
