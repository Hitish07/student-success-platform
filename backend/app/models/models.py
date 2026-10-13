from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("department_id", "code", name="uq_subjects_department_code"),
        UniqueConstraint("department_id", "name", "year", "semester", name="uq_subjects_department_name_year_semester"),
        CheckConstraint("year BETWEEN 1 AND 4", name="ck_subjects_year"),
        CheckConstraint("semester IN (1, 2)", name="ck_subjects_semester"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
        CheckConstraint("year BETWEEN 1 AND 4", name="ck_student_profiles_year"),
        CheckConstraint("semester IN (1, 2)", name="ck_student_profiles_semester"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_faculty_profiles_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FacultySubject(Base):
    __tablename__ = "faculty_subjects"
    __table_args__ = (UniqueConstraint("faculty_id", "subject_id", name="uq_faculty_subjects_faculty_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'faculty', 'dean', 'principal')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def name(self) -> str:
        return self.full_name

    @name.setter
    def name(self, value: str) -> None:
        self.full_name = value.strip()


class AuthRefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        UniqueConstraint("jti", name="uq_auth_refresh_tokens_jti"),
        Index("ix_auth_refresh_tokens_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("max_marks > 0", name="ck_assignments_max_marks_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    max_marks: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_assignment_submissions_assignment_student",
        ),
        CheckConstraint("marks IS NULL OR marks >= 0", name="ck_assignment_submissions_marks_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    marks: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    feedback: Mapped[str | None] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text)


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (CheckConstraint("credits > 0", name="ck_courses_credits_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            "semester",
            name="uq_enrollments_student_course_semester",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    semester: Mapped[str] = mapped_column(String(32), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("status IN ('present', 'absent', 'late', 'excused')", name="ck_attendance_status"),
        UniqueConstraint("student_id", "course_id", "class_date", name="uq_attendance_student_course_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    class_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (CheckConstraint("max_score > 0", name="ck_assessments_max_score_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)


class Mark(Base):
    __tablename__ = "marks"
    __table_args__ = (
        UniqueConstraint("student_id", "assessment_id", name="uq_marks_student_assessment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class StudentNote(Base):
    __tablename__ = "student_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Intervention(Base):
    __tablename__ = "interventions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('assigned', 'in_progress', 'completed', 'cancelled')",
            name="ck_interventions_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="assigned", server_default="assigned", nullable=False)


class InterventionOutcome(Base):
    __tablename__ = "intervention_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "intervention_id",
            name="uq_intervention_outcomes_intervention_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(
        ForeignKey("interventions.id", ondelete="CASCADE"),
        nullable=False,
    )
    before_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    after_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    comparison_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    caveats: Mapped[str | None] = mapped_column(Text)


class FacultyFeedback(Base):
    __tablename__ = "faculty_feedback"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_faculty_feedback_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentFeedback(Base):
    __tablename__ = "student_feedback"
    __table_args__ = (
        Index("ix_student_feedback_student_created", "student_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FacultyEvaluation(Base):
    __tablename__ = "faculty_evaluations"
    __table_args__ = (
        UniqueConstraint("faculty_id", "period", name="uq_faculty_evaluations_faculty_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    feedback_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    outcome_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    attendance_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), nullable=False)


class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 1", name="ck_risk_scores_range"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_risk_scores_level"),
        Index("ix_risk_scores_student_computed", "student_id", "computed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(12), nullable=False)
    contributing_factors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_alerts_severity",
        ),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="ck_alerts_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", server_default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AcademicSourceRecord(Base):
    __tablename__ = "source_academic_records"
    __table_args__ = (Index("ix_source_academic_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    marks_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    backlog_count: Mapped[int | None] = mapped_column(Integer)
    term: Mapped[str | None] = mapped_column(String(32))


class AttendanceSourceRecord(Base):
    __tablename__ = "source_attendance_records"
    __table_args__ = (Index("ix_source_attendance_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_code: Mapped[str | None] = mapped_column(String(40))
    attendance_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class LmsSourceRecord(Base):
    __tablename__ = "source_lms_records"
    __table_args__ = (Index("ix_source_lms_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    login_count: Mapped[int | None] = mapped_column(Integer)
    assignment_completion_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class EngagementSourceRecord(Base):
    __tablename__ = "source_engagement_records"
    __table_args__ = (Index("ix_source_engagement_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_count: Mapped[int | None] = mapped_column(Integer)


class PlacementSourceRecord(Base):
    __tablename__ = "source_placement_records"
    __table_args__ = (Index("ix_source_placement_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    aptitude_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    coding_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    mock_interview_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class SkillsSourceRecord(Base):
    __tablename__ = "source_skills_records"
    __table_args__ = (Index("ix_source_skills_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    soft_skill_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class FeedbackSourceRecord(Base):
    __tablename__ = "source_feedback_records"
    __table_args__ = (Index("ix_source_feedback_external_id", "external_student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_student_id: Mapped[str] = mapped_column(String(80), nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    category: Mapped[str | None] = mapped_column(String(40))
