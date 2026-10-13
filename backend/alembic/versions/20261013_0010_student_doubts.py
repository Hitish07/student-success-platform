"""Add student doubts table.

Revision ID: 20261013_0010
Revises: 20261013_0009
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0010"
down_revision: str | None = "20261013_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_doubts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_student_doubts_student",
        "student_doubts",
        ["student_id", "created_at"],
    )
    op.create_index(
        "ix_student_doubts_subject",
        "student_doubts",
        ["subject_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_doubts_subject", table_name="student_doubts")
    op.drop_index("ix_student_doubts_student", table_name="student_doubts")
    op.drop_table("student_doubts")
