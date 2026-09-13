"""Add the vocabulary catalog identity constraint required by content imports.

Revision ID: e1a2b3c4d5f6
Revises: c4e6a8f1b2d3
Create Date: 2026-09-13

The upgrade intentionally fails if an existing database already has duplicate
word/POS rows.  It must not silently discard or merge curated vocabulary.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e1a2b3c4d5f6"
down_revision: str = "c4e6a8f1b2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "uq_vocab_word_pos"
def upgrade() -> None:
    op.create_unique_constraint(
        _CONSTRAINT_NAME, "vocabulary_items", ["word", "part_of_speech"]
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT_NAME, "vocabulary_items", type_="unique")
