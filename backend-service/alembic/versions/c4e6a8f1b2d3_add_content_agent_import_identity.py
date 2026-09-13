"""Add durable identity reservation for approved course imports.

Revision ID: c4e6a8f1b2d3
Revises: 4a7b1c9e2d30
Create Date: 2026-09-11

Existing jobs intentionally remain NULL: historical request hashes cannot
reliably reconstruct the approved artifact, source pins, and generation key.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4e6a8f1b2d3"
down_revision: str = "4a7b1c9e2d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A regular unique index permits multiple NULLs on both supported SQLite
    # and PostgreSQL, while uniquely reserving every non-NULL identity.
    op.add_column(
        "content_agent_jobs",
        sa.Column("import_identity", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_content_agent_jobs_import_identity",
        "content_agent_jobs",
        ["import_identity"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_content_agent_jobs_import_identity",
        table_name="content_agent_jobs",
    )
    op.drop_column("content_agent_jobs", "import_identity")
