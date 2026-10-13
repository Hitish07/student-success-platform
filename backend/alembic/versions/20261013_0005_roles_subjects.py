"""Add subjects, student/faculty profiles and align source index names.

Revision ID: 20261013_0005
Revises: 20261012_0004
"""
import sqlalchemy as sa
from alembic import op

revision = "20261013_0005"
down_revision = "20261012_0004"
branch_labels = None
depends_on = None

SOURCES = ["academic", "attendance", "engagement", "feedback", "lms", "placement", "skills"]


def _created_at():
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("department_id", "code", name="uq_subjects_department_code"),
        sa.UniqueConstraint(
            "department_id", "name", "year", "semester",
            name="uq_subjects_department_name_year_semester",
        ),
    )
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        _created_at(),
        sa.UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
    )
    op.create_table(
        "faculty_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        _created_at(),
        sa.UniqueConstraint("user_id", name="uq_faculty_profiles_user_id"),
    )
    op.create_table(
        "faculty_subjects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        _created_at(),
        sa.UniqueConstraint("faculty_id", "subject_id", name="uq_faculty_subjects_faculty_subject"),
    )
    for name in SOURCES:
        table = f"source_{name}_records"
        op.drop_index(f"ix_source_{name}_records_external_id", table_name=table)
        op.create_index(f"ix_source_{name}_external_id", table, ["external_student_id"])


def downgrade() -> None:
    for name in SOURCES:
        table = f"source_{name}_records"
        op.drop_index(f"ix_source_{name}_external_id", table_name=table)
        op.create_index(f"ix_source_{name}_records_external_id", table, ["external_student_id"])
    op.drop_table("faculty_subjects")
    op.drop_table("faculty_profiles")
    op.drop_table("student_profiles")
    op.drop_table("subjects")
