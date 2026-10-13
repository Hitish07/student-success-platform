"""Add subject assignments and student submissions.

Revision ID: 20261013_0006
Revises: 20261013_0005
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261013_0006"
down_revision: str | None = "20261013_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "faculty_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("max_marks", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("max_marks > 0", name="ck_assignments_max_marks_positive"),
    )
    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
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
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("marks", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_assignment_submissions_assignment_student",
        ),
        sa.CheckConstraint(
            "marks IS NULL OR marks >= 0",
            name="ck_assignment_submissions_marks_nonnegative",
        ),
    )


def downgrade() -> None:
    op.drop_table("assignment_submissions")
    op.drop_table("assignments")
