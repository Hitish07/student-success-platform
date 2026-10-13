from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcademicSourceRecord,
    AttendanceSourceRecord,
    Department,
    EngagementSourceRecord,
    Enrollment,
    FeedbackSourceRecord,
    LmsSourceRecord,
    PlacementSourceRecord,
    SkillsSourceRecord,
    User,
)


def students(db: Session, department_id: int | None = None) -> list[User]:
    statement = select(User).where(User.role == "student")
    if department_id is not None:
        statement = statement.where(User.department_id == department_id)
    return list(db.scalars(statement.order_by(User.id)).all())


def departments(db: Session) -> dict[int, str]:
    return {department.id: department.name for department in db.scalars(select(Department))}


def cohorts(db: Session, student_ids: list[int]) -> dict[int, str]:
    if not student_ids:
        return {}
    statement = (
        select(Enrollment.student_id, Enrollment.semester)
        .where(Enrollment.student_id.in_(student_ids))
        .order_by(Enrollment.semester, Enrollment.id)
    )
    result: dict[int, str] = {}
    for student_id, semester in db.execute(statement):
        result.setdefault(student_id, semester)
    return result


def academic_records(db: Session) -> list[AcademicSourceRecord]:
    return list(db.scalars(select(AcademicSourceRecord).order_by(AcademicSourceRecord.id)).all())


def attendance_records(db: Session) -> list[AttendanceSourceRecord]:
    return list(db.scalars(select(AttendanceSourceRecord).order_by(AttendanceSourceRecord.id)).all())


def lms_records(db: Session) -> list[LmsSourceRecord]:
    return list(db.scalars(select(LmsSourceRecord).order_by(LmsSourceRecord.id)).all())


def engagement_records(db: Session) -> list[EngagementSourceRecord]:
    return list(db.scalars(select(EngagementSourceRecord).order_by(EngagementSourceRecord.id)).all())


def placement_records(db: Session) -> list[PlacementSourceRecord]:
    return list(db.scalars(select(PlacementSourceRecord).order_by(PlacementSourceRecord.id)).all())


def skills_records(db: Session) -> list[SkillsSourceRecord]:
    return list(db.scalars(select(SkillsSourceRecord).order_by(SkillsSourceRecord.id)).all())


def feedback_records(db: Session) -> list[FeedbackSourceRecord]:
    return list(db.scalars(select(FeedbackSourceRecord).order_by(FeedbackSourceRecord.id)).all())
