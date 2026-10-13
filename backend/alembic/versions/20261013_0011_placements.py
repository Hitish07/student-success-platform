"""Add placements table.

Revision ID: 20261013_0011
Revises: 20261013_0010
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0011"
down_revision: str | None = "20261013_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "placements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=160), nullable=False),
        sa.Column("package_lpa", sa.Numeric(6, 2), nullable=True),
        sa.Column("offer_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="offered",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('offered', 'accepted', 'declined', 'joined')",
            name="ck_placements_status",
        ),
    )
    op.create_index("ix_placements_student", "placements", ["student_id", "offer_date"])
    op.create_index("ix_placements_offer_date", "placements", ["offer_date"])


def downgrade() -> None:
    op.drop_index("ix_placements_offer_date", table_name="placements")
    op.drop_index("ix_placements_student", table_name="placements")
    op.drop_table("placements")
