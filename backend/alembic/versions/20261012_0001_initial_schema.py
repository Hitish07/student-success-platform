"""Create the initial student success schema.

Revision ID: 20261012_0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261012_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("code", sa.String(12), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT")),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('student', 'faculty', 'dean', 'principal')", name="ck_users_role"),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.CheckConstraint("credits > 0", name="ck_courses_credits_positive"),
    )
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester", sa.String(32), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "course_id", "semester", name="uq_enrollments_student_course_semester"),
    )
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.CheckConstraint("status IN ('present', 'absent', 'late', 'excused')", name="ck_attendance_status"),
        sa.UniqueConstraint("student_id", "course_id", "class_date", name="uq_attendance_student_course_date"),
    )
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("assessment_type", sa.String(32), nullable=False),
        sa.Column("max_score", sa.Numeric(7, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.CheckConstraint("max_score > 0", name="ck_assessments_max_score_positive"),
    )
    op.create_table(
        "marks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(7, 2), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("is_submitted", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("student_id", "assessment_id", name="uq_marks_student_assessment"),
    )
    op.create_table(
        "student_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "interventions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("intervention_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="assigned", nullable=False),
        sa.CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_interventions_status",
        ),
    )
    op.create_table(
        "intervention_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intervention_id", sa.Integer(), sa.ForeignKey("interventions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("before_metrics", sa.JSON(), nullable=False),
        sa.Column("after_metrics", sa.JSON()),
        sa.Column("comparison_metrics", sa.JSON()),
        sa.Column("measured_at", sa.DateTime(timezone=True)),
        sa.Column("caveats", sa.Text()),
        sa.UniqueConstraint("intervention_id", name="uq_intervention_outcomes_intervention_id"),
    )
    op.create_table(
        "faculty_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="SET NULL")),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_faculty_feedback_rating"),
    )
    op.create_table(
        "faculty_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(32), nullable=False),
        sa.Column("feedback_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("outcome_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("attendance_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("overall_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("formula_version", sa.String(32), nullable=False),
        sa.UniqueConstraint("faculty_id", "period", name="uq_faculty_evaluations_faculty_period"),
    )
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_level", sa.String(12), nullable=False),
        sa.Column("contributing_factors", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 1", name="ck_risk_scores_range"),
        sa.CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_risk_scores_level"),
    )
    op.create_index("ix_risk_scores_student_computed", "risk_scores", ["student_id", "computed_at"])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_alerts_severity"),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="ck_alerts_status"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("alerts")
    op.drop_index("ix_risk_scores_student_computed", table_name="risk_scores")
    op.drop_table("risk_scores")
    op.drop_table("faculty_evaluations")
    op.drop_table("faculty_feedback")
    op.drop_table("intervention_outcomes")
    op.drop_table("interventions")
    op.drop_table("student_notes")
    op.drop_table("marks")
    op.drop_table("assessments")
    op.drop_table("attendance")
    op.drop_table("enrollments")
    op.drop_table("courses")
    op.drop_table("users")
    op.drop_table("departments")
