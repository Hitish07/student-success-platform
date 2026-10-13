"""Add assignment attempts and tab switch tracking.

Revision ID: 20261013_0009
Revises: 20261013_0008
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0009"
down_revision: str | None = "20261013_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assignment_submissions",
        sa.Column("tab_switches", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "assignment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
        sa.Column("tab_switches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'voided', 'submitted')",
            name="ck_assignment_attempts_status",
        ),
        sa.CheckConstraint(
            "tab_switches >= 0",
            name="ck_assignment_attempts_tab_switches",
        ),
    )
    op.create_index(
        "ix_assignment_attempts_assignment_student",
        "assignment_attempts",
        ["assignment_id", "student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_assignment_attempts_assignment_student", table_name="assignment_attempts")
    op.drop_table("assignment_attempts")
    op.drop_column("assignment_submissions", "tab_switches")
