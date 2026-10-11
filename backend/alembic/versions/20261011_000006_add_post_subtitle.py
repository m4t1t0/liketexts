"""Add posts.subtitle (optional Substack-style subtitle, defaults to '')."""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("subtitle", sa.String(500), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("posts", "subtitle")
