from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Assessment,
    Attendance,
    Course,
    Enrollment,
    FacultyFeedback,
    Intervention,
    Mark,
    RiskScore,
    StudentNote,
    User,
)


def faculty_courses(db: Session, faculty_id: int) -> list[tuple[Course, int]]:
    statement = (
        select(Course, func.count(Enrollment.id))
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.faculty_id == faculty_id)
        .group_by(Course.id)
        .order_by(Course.code)
    )
    return list(db.execute(statement).all())


def assigned_student_ids(db: Session, faculty_id: int) -> list[int]:
    statement = (
        select(Enrollment.student_id)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Course.faculty_id == faculty_id)
        .distinct()
    )
    return list(db.scalars(statement).all())


def student_is_assigned(db: Session, faculty_id: int, student_id: int) -> bool:
    return (
        db.scalar(
            select(Enrollment.id)
            .join(Course, Enrollment.course_id == Course.id)
            .where(
                Enrollment.student_id == student_id,
                Course.faculty_id == faculty_id,
            )
            .limit(1)
        )
        is not None
    )


def course_is_assigned(db: Session, faculty_id: int, course_id: int) -> bool:
    return (
        db.scalar(
            select(Course.id).where(
                Course.id == course_id,
                Course.faculty_id == faculty_id,
            )
        )
        is not None
    )


def student_is_enrolled(
    db: Session,
    faculty_id: int,
    course_id: int,
    student_id: int,
) -> bool:
    return (
        db.scalar(
            select(Enrollment.id)
            .join(Course, Enrollment.course_id == Course.id)
            .where(
                Course.id == course_id,
                Course.faculty_id == faculty_id,
                Enrollment.student_id == student_id,
            )
        )
        is not None
    )


def students_for_course(
    db: Session,
    faculty_id: int,
    course_id: int,
) -> list[User]:
    statement = (
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.id == course_id, Course.faculty_id == faculty_id)
        .order_by(User.full_name, User.id)
        .distinct()
    )
    return list(db.scalars(statement).all())


def student_progress(
    db: Session,
    faculty_id: int,
    course_id: int,
    student_ids: list[int],
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[float, float]]]:
    if not student_ids:
        return {}, {}
    attendance_statement = (
        select(
            Attendance.student_id,
            func.sum(case((Attendance.status.in_(("present", "late")), 1), else_=0)),
            func.count(Attendance.id),
        )
        .where(
            Attendance.course_id == course_id,
            Attendance.student_id.in_(student_ids),
            Attendance.status != "excused",
        )
        .group_by(Attendance.student_id)
    )
    attendance = {
        student_id: (int(present or 0), int(total or 0))
        for student_id, present, total in db.execute(attendance_statement)
    }
    mark_statement = (
        select(Mark.student_id, func.sum(Mark.score), func.sum(Assessment.max_score))
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .where(
            Assessment.course_id == course_id,
            Assessment.course_id.in_(
                select(Course.id).where(Course.faculty_id == faculty_id)
            ),
            Mark.student_id.in_(student_ids),
            Mark.is_submitted.is_(True),
        )
        .group_by(Mark.student_id)
    )
    marks = {
        student_id: (float(score or 0), float(max_score or 0))
        for student_id, score, max_score in db.execute(mark_statement)
    }
    return attendance, marks


def latest_risks(
    db: Session,
    faculty_id: int,
    student_ids: list[int] | None = None,
) -> list[tuple[RiskScore, User]]:
    if student_ids is None:
        student_ids = assigned_student_ids(db, faculty_id)
    if not student_ids:
        return []
    statement = (
        select(RiskScore, User)
        .join(User, User.id == RiskScore.student_id)
        .where(RiskScore.student_id.in_(student_ids))
        .order_by(RiskScore.computed_at.desc(), RiskScore.id.desc())
    )
    latest_by_student: dict[int, tuple[RiskScore, User]] = {}
    for risk, student in db.execute(statement):
        latest_by_student.setdefault(student.id, (risk, student))
    return list(latest_by_student.values())


def student_course_codes(db: Session, faculty_id: int, student_id: int) -> list[str]:
    statement = (
        select(Course.code)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student_id,
            Course.faculty_id == faculty_id,
        )
        .order_by(Course.code)
    )
    return list(db.scalars(statement).all())


def open_alert_counts(db: Session, student_ids: list[int]) -> dict[int, int]:
    if not student_ids:
        return {}
    statement = (
        select(Alert.student_id, func.count(Alert.id))
        .where(Alert.student_id.in_(student_ids), Alert.status != "resolved")
        .group_by(Alert.student_id)
    )
    return {student_id: int(count) for student_id, count in db.execute(statement)}


def assigned_assessments(
    db: Session,
    faculty_id: int,
    course_id: int,
) -> list[Assessment]:
    statement = (
        select(Assessment)
        .join(Course, Course.id == Assessment.course_id)
        .where(Course.id == course_id, Course.faculty_id == faculty_id)
        .order_by(Assessment.due_date, Assessment.id)
    )
    return list(db.scalars(statement).all())


def assessment_for_faculty(
    db: Session,
    faculty_id: int,
    assessment_id: int,
) -> Assessment | None:
    statement = (
        select(Assessment)
        .join(Course, Course.id == Assessment.course_id)
        .where(Assessment.id == assessment_id, Course.faculty_id == faculty_id)
    )
    return db.scalar(statement)


def attendance_for_faculty(db: Session, faculty_id: int) -> list[tuple[Attendance, User, Course]]:
    statement = (
        select(Attendance, User, Course)
        .join(Course, Course.id == Attendance.course_id)
        .join(User, User.id == Attendance.student_id)
        .join(
            Enrollment,
            (Enrollment.course_id == Attendance.course_id)
            & (Enrollment.student_id == Attendance.student_id),
        )
        .where(Course.faculty_id == faculty_id)
        .order_by(Attendance.class_date.desc(), Attendance.id.desc())
        .distinct()
    )
    return list(db.execute(statement).all())


def attendance_record(
    db: Session,
    faculty_id: int,
    attendance_id: int,
) -> Attendance | None:
    return db.scalar(
        select(Attendance)
        .join(Course, Course.id == Attendance.course_id)
        .join(
            Enrollment,
            (Enrollment.course_id == Attendance.course_id)
            & (Enrollment.student_id == Attendance.student_id),
        )
        .where(Attendance.id == attendance_id, Course.faculty_id == faculty_id)
    )


def marks_for_course(db: Session, faculty_id: int, course_id: int) -> list[tuple[Mark, User, Assessment]]:
    statement = (
        select(Mark, User, Assessment)
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .join(Course, Course.id == Assessment.course_id)
        .join(User, User.id == Mark.student_id)
        .join(
            Enrollment,
            (Enrollment.course_id == Course.id)
            & (Enrollment.student_id == Mark.student_id),
        )
        .where(Course.id == course_id, Course.faculty_id == faculty_id)
        .order_by(Assessment.due_date, User.full_name)
        .distinct()
    )
    return list(db.execute(statement).all())


def mark_record(db: Session, faculty_id: int, mark_id: int) -> Mark | None:
    return db.scalar(
        select(Mark)
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .join(Course, Course.id == Assessment.course_id)
        .join(
            Enrollment,
            (Enrollment.course_id == Course.id)
            & (Enrollment.student_id == Mark.student_id),
        )
        .where(Mark.id == mark_id, Course.faculty_id == faculty_id)
    )


def notes_for_student(
    db: Session,
    faculty_id: int,
    student_id: int,
) -> list[tuple[StudentNote, User]]:
    statement = (
        select(StudentNote, User)
        .join(User, User.id == StudentNote.author_id)
        .join(Enrollment, Enrollment.student_id == StudentNote.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(StudentNote.student_id == student_id, Course.faculty_id == faculty_id)
        .order_by(StudentNote.created_at.desc(), StudentNote.id.desc())
        .distinct()
    )
    return list(db.execute(statement).all())


def note_record(db: Session, faculty_id: int, note_id: int) -> StudentNote | None:
    return db.scalar(
        select(StudentNote)
        .join(Enrollment, Enrollment.student_id == StudentNote.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(StudentNote.id == note_id, Course.faculty_id == faculty_id)
        .distinct()
    )


def interventions_for_student(db: Session, faculty_id: int, student_id: int) -> list[Intervention]:
    statement = (
        select(Intervention)
        .join(Enrollment, Enrollment.student_id == Intervention.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Intervention.student_id == student_id, Course.faculty_id == faculty_id)
        .order_by(Intervention.start_date.desc(), Intervention.id.desc())
        .distinct()
    )
    return list(db.scalars(statement).all())


def alerts_for_faculty(db: Session, faculty_id: int) -> list[tuple[Alert, User]]:
    student_ids = assigned_student_ids(db, faculty_id)
    if not student_ids:
        return []
    statement = (
        select(Alert, User)
        .join(User, User.id == Alert.student_id)
        .where(Alert.student_id.in_(student_ids), Alert.status != "resolved")
        .order_by(Alert.created_at.desc(), Alert.id.desc())
    )
    return list(db.execute(statement).all())


def feedback_for_faculty(
    db: Session,
    faculty_id: int,
) -> list[tuple[FacultyFeedback, User, Course | None]]:
    statement = (
        select(FacultyFeedback, User, Course)
        .join(User, User.id == FacultyFeedback.student_id)
        .outerjoin(Course, Course.id == FacultyFeedback.course_id)
        .where(
            FacultyFeedback.faculty_id == faculty_id,
            (FacultyFeedback.course_id.is_(None)) | (Course.faculty_id == faculty_id),
        )
        .order_by(FacultyFeedback.submitted_at.desc(), FacultyFeedback.id.desc())
    )
    return list(db.execute(statement).all())
