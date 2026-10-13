"""Add external source records for student success data integration.

Revision ID: 20261012_0004
Revises: 20261012_0003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261012_0004"
down_revision: Union[str, None] = "20261012_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_source_table(table_name: str, columns: list[sa.Column]) -> None:
    op.create_table(table_name, sa.Column("id", sa.Integer(), primary_key=True), *columns)
    op.create_index(
        f"ix_{table_name}_external_id",
        table_name,
        ["external_student_id"],
    )


def upgrade() -> None:
    _create_source_table(
        "source_academic_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("cgpa", sa.Numeric(5, 2)),
            sa.Column("marks_percentage", sa.Numeric(6, 2)),
            sa.Column("backlog_count", sa.Integer()),
            sa.Column("term", sa.String(32)),
        ],
    )
    _create_source_table(
        "source_attendance_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("subject_code", sa.String(40)),
            sa.Column("attendance_percentage", sa.Numeric(6, 2)),
        ],
    )
    _create_source_table(
        "source_lms_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("login_count", sa.Integer()),
            sa.Column("assignment_completion_percentage", sa.Numeric(6, 2)),
        ],
    )
    _create_source_table(
        "source_engagement_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("activity_type", sa.String(32), nullable=False),
            sa.Column("activity_count", sa.Integer()),
        ],
    )
    _create_source_table(
        "source_placement_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("aptitude_score", sa.Numeric(6, 2)),
            sa.Column("coding_score", sa.Numeric(6, 2)),
            sa.Column("mock_interview_score", sa.Numeric(6, 2)),
        ],
    )
    _create_source_table(
        "source_skills_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("technical_score", sa.Numeric(6, 2)),
            sa.Column("soft_skill_score", sa.Numeric(6, 2)),
        ],
    )
    _create_source_table(
        "source_feedback_records",
        [
            sa.Column("external_student_id", sa.String(80), nullable=False),
            sa.Column("rating", sa.Numeric(4, 2)),
            sa.Column("category", sa.String(40)),
        ],
    )


def downgrade() -> None:
    for table_name in (
        "source_feedback_records",
        "source_skills_records",
        "source_placement_records",
        "source_engagement_records",
        "source_lms_records",
        "source_attendance_records",
        "source_academic_records",
    ):
        op.drop_index(f"ix_{table_name}_external_id", table_name=table_name)
        op.drop_table(table_name)
