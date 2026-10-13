from decimal import Decimal

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    Attendance,
    Course,
    Enrollment,
    FacultyFeedback,
    Intervention,
    Mark,
    RiskScore,
    StudentFeedback,
    User,
)


def enrolled_courses(db: Session, student_id: int) -> list[tuple[Enrollment, Course, User]]:
    statement = (
        select(Enrollment, Course, User)
        .join(Course, Enrollment.course_id == Course.id)
        .join(User, Course.faculty_id == User.id)
        .where(Enrollment.student_id == student_id)
        .order_by(Course.code)
    )
    return list(db.execute(statement).all())


def attendance_totals(db: Session, student_id: int) -> dict[int, tuple[int, int]]:
    attended = func.sum(
        case(
            (Attendance.status.in_(("present", "late")), 1),
            else_=0,
        )
    )
    statement = (
        select(Attendance.course_id, attended, func.count(Attendance.id))
        .where(
            Attendance.student_id == student_id,
            Attendance.status != "excused",
        )
        .group_by(Attendance.course_id)
    )
    return {
        course_id: (int(present or 0), int(total or 0))
        for course_id, present, total in db.execute(statement)
    }


def assessment_totals(
    db: Session,
    student_id: int,
) -> dict[int, tuple[Decimal | None, Decimal | None, int, int]]:
    statement = (
        select(
            Assessment.course_id,
            func.sum(Mark.score),
            func.sum(Assessment.max_score),
            func.sum(cast(Mark.is_submitted, Integer)),
            func.count(Assessment.id),
        )
        .join(Mark, Mark.assessment_id == Assessment.id)
        .where(Mark.student_id == student_id)
        .group_by(Assessment.course_id)
    )
    return {
        course_id: (score, max_score, int(completed or 0), int(total or 0))
        for course_id, score, max_score, completed, total in db.execute(statement)
    }


def latest_risk_score(db: Session, student_id: int) -> RiskScore | None:
    return db.scalar(
        select(RiskScore)
        .where(RiskScore.student_id == student_id)
        .order_by(RiskScore.computed_at.desc(), RiskScore.id.desc())
        .limit(1)
    )


def student_attendance(db: Session, student_id: int) -> list[tuple[Attendance, Course]]:
    statement = (
        select(Attendance, Course)
        .join(Course, Attendance.course_id == Course.id)
        .where(Attendance.student_id == student_id)
        .order_by(Attendance.class_date.desc(), Attendance.id.desc())
    )
    return list(db.execute(statement).all())


def student_marks(db: Session, student_id: int) -> list[tuple[Mark, Assessment, Course]]:
    statement = (
        select(Mark, Assessment, Course)
        .join(Assessment, Mark.assessment_id == Assessment.id)
        .join(Course, Assessment.course_id == Course.id)
        .where(Mark.student_id == student_id)
        .order_by(Assessment.due_date.desc(), Mark.id.desc())
    )
    return list(db.execute(statement).all())


def student_interventions(db: Session, student_id: int) -> list[Intervention]:
    statement = (
        select(Intervention)
        .where(Intervention.student_id == student_id)
        .order_by(Intervention.start_date.desc(), Intervention.id.desc())
    )
    return list(db.scalars(statement).all())


def received_feedback(
    db: Session,
    student_id: int,
) -> list[tuple[StudentFeedback, User, Course | None]]:
    statement = (
        select(StudentFeedback, User, Course)
        .join(User, StudentFeedback.faculty_id == User.id)
        .outerjoin(Course, StudentFeedback.course_id == Course.id)
        .where(StudentFeedback.student_id == student_id)
        .order_by(StudentFeedback.created_at.desc(), StudentFeedback.id.desc())
    )
    return list(db.execute(statement).all())


def submitted_feedback(
    db: Session,
    student_id: int,
) -> list[tuple[FacultyFeedback, User, Course]]:
    statement = (
        select(FacultyFeedback, User, Course)
        .join(User, FacultyFeedback.faculty_id == User.id)
        .join(Course, FacultyFeedback.course_id == Course.id)
        .where(FacultyFeedback.student_id == student_id)
        .order_by(FacultyFeedback.submitted_at.desc(), FacultyFeedback.id.desc())
    )
    return list(db.execute(statement).all())


def create_course_feedback(
    db: Session,
    *,
    student_id: int,
    faculty_id: int,
    course_id: int,
    rating: int,
    comments: str | None,
) -> FacultyFeedback | None:
    enrolled = db.scalar(
        select(Enrollment.id).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
        )
    )
    assigned = db.scalar(
        select(Course.id).where(
            Course.id == course_id,
            Course.faculty_id == faculty_id,
        )
    )
    if enrolled is None or assigned is None:
        return None

    feedback = FacultyFeedback(
        student_id=student_id,
        faculty_id=faculty_id,
        course_id=course_id,
        rating=rating,
        comments=comments,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
