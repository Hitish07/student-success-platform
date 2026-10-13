"""Student 360: an aggregated view of one student for their own faculty.

Scoped so that a faculty member can only read a student who is in one of
their own subjects. Returns no data for students outside that scope (404,
not 403, so existence is not confirmed).
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    Assignment,
    AssignmentSubmission,
    Attendance,
    Course,
    Department,
    FacultySubject,
    Mark,
    RiskScore,
    StudentDoubt,
    StudentProfile,
    Subject,
    User,
)
from app.repositories import student_portal as repository
from app.schemas.faculty_portal import (
    Student360Doubt,
    Student360Header,
    Student360JourneyEvent,
    Student360Metrics,
    Student360Risk,
    Student360Submission,
    Student360View,
)


JOURNEY_LIMIT = 10
DOUBTS_LIMIT = 5
SUBMISSIONS_LIMIT = 5


def _faculty_subject_ids(db: Session, faculty: User) -> list[int]:
    return list(
        db.execute(
            select(FacultySubject.subject_id).where(FacultySubject.faculty_id == faculty.id)
        ).scalars().all()
    )


def _scoped_student(db: Session, faculty: User, student_id: int) -> tuple[User, StudentProfile]:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    student = db.get(User, student_id)
    if student is None or student.role != "student" or profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    my_subjects = _faculty_subject_ids(db, faculty)
    if not my_subjects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    in_my_class = db.scalar(
        select(Subject.id)
        .where(Subject.id.in_(my_subjects))
        .where(Subject.department_id == profile.department_id)
        .where(Subject.year == profile.year)
        .where(Subject.semester == profile.semester)
    )
    if in_my_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return student, profile


def _header(db: Session, student: User, profile: StudentProfile) -> Student360Header:
    department = db.get(Department, profile.department_id)
    return Student360Header(
        student_id=student.id,
        full_name=student.full_name,
        email=student.email,
        department=department.name if department else None,
        year=profile.year,
        semester=profile.semester,
    )


def _risk(db: Session, student_id: int) -> Student360Risk:
    row = db.scalar(
        select(RiskScore)
        .where(RiskScore.student_id == student_id)
        .order_by(RiskScore.computed_at.desc(), RiskScore.id.desc())
    )
    if row is None:
        return Student360Risk(score=None, level=None, computed_at=None)
    return Student360Risk(
        score=float(row.score) if row.score is not None else None,
        level=row.level,
        computed_at=row.computed_at,
    )


def _metrics(db: Session, student_id: int) -> Student360Metrics:
    attendance_rows = db.execute(
        select(Attendance.status).where(Attendance.student_id == student_id)
    ).scalars().all()
    if attendance_rows:
        present = sum(1 for s in attendance_rows if s in ("present", "late"))
        attendance_percentage = round(present / len(attendance_rows) * 100.0, 2)
    else:
        attendance_percentage = None

    marks_rows = db.execute(
        select(Mark.score, Assessment.max_score)
        .join(Assessment, Assessment.id == Mark.assessment_id)
        .where(Mark.student_id == student_id, Mark.is_submitted.is_(True))
    ).all()
    percentages = [
        float(score) / float(max_score) * 100.0
        for score, max_score in marks_rows
        if max_score is not None and float(max_score) > 0
    ]
    marks_percentage = round(sum(percentages) / len(percentages), 2) if percentages else None

    submitted_assignments = (
        db.scalar(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(AssignmentSubmission.student_id == student_id)
        )
        or 0
    )

    # Pending = assignments whose subject matches the student's profile
    # and that have no submission row yet.
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    pending_assignments = 0
    if profile is not None:
        total_assignments = (
            db.scalar(
                select(func.count())
                .select_from(Assignment)
                .join(Subject, Subject.id == Assignment.subject_id)
                .where(
                    Subject.department_id == profile.department_id,
                    Subject.year == profile.year,
                    Subject.semester == profile.semester,
                )
            )
            or 0
        )
        pending_assignments = max(0, int(total_assignments) - int(submitted_assignments))

    return Student360Metrics(
        attendance_percentage=attendance_percentage,
        marks_percentage=marks_percentage,
        pending_assignments=pending_assignments,
        submitted_assignments=int(submitted_assignments),
    )


def _journey(db: Session, student_id: int) -> list[Student360JourneyEvent]:
    events: list[Student360JourneyEvent] = []

    for enrollment, course, _faculty in repository.enrolled_courses(db, student_id):
        events.append(
            Student360JourneyEvent(
                occurred_at=enrollment.enrolled_at,
                event_type="course",
                title=f"Enrolled in {course.name}",
                description=f"{course.code}",
            )
        )

    for attendance, course in repository.student_attendance(db, student_id):
        events.append(
            Student360JourneyEvent(
                occurred_at=datetime.combine(
                    attendance.class_date, datetime.min.time(), timezone.utc
                ),
                event_type="attendance",
                title=f"{attendance.status.title()} - {course.code}",
                description=f"{course.name} class on {attendance.class_date.isoformat()}.",
            )
        )

    for mark, assessment, course in repository.student_marks(db, student_id):
        submitted_at = mark.submitted_at or datetime.combine(
            assessment.due_date, datetime.min.time(), timezone.utc
        )
        state = "Submitted" if mark.is_submitted else "Missed"
        events.append(
            Student360JourneyEvent(
                occurred_at=submitted_at,
                event_type="assessment",
                title=f"{state} - {assessment.title}",
                description=(
                    f"{course.code} - {float(mark.score):g} of "
                    f"{float(assessment.max_score):g} points."
                ),
            )
        )

    for intervention in repository.student_interventions(db, student_id):
        events.append(
            Student360JourneyEvent(
                occurred_at=datetime.combine(
                    intervention.start_date, datetime.min.time(), timezone.utc
                ),
                event_type="support",
                title=f"{intervention.intervention_type.replace('_', ' ').title()} - "
                f"{intervention.status.replace('_', ' ').title()}",
                description=intervention.description,
            )
        )

    for feedback, faculty, course in repository.received_feedback(db, student_id):
        events.append(
            Student360JourneyEvent(
                occurred_at=feedback.created_at,
                event_type="feedback",
                title=f"Feedback from {faculty.full_name}",
                description=(
                    f"{course.code}: {feedback.message}" if course else feedback.message
                ),
            )
        )

    events.sort(key=lambda item: item.occurred_at, reverse=True)
    return events[:JOURNEY_LIMIT]


def _doubts(db: Session, student_id: int) -> list[Student360Doubt]:
    rows = db.execute(
        select(StudentDoubt, Subject)
        .join(Subject, Subject.id == StudentDoubt.subject_id)
        .where(StudentDoubt.student_id == student_id)
        .order_by(StudentDoubt.created_at.desc(), StudentDoubt.id.desc())
        .limit(DOUBTS_LIMIT)
    ).all()
    return [
        Student360Doubt(
            subject_code=subject.code,
            subject_name=subject.name,
            asked_at=doubt.created_at,
        )
        for doubt, subject in rows
    ]


def _submissions(db: Session, student_id: int) -> list[Student360Submission]:
    rows = db.execute(
        select(AssignmentSubmission, Assignment, Subject)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .join(Subject, Subject.id == Assignment.subject_id)
        .where(AssignmentSubmission.student_id == student_id)
        .order_by(
            AssignmentSubmission.submitted_at.desc(),
            AssignmentSubmission.id.desc(),
        )
        .limit(SUBMISSIONS_LIMIT)
    ).all()
    return [
        Student360Submission(
            assignment_title=assignment.title,
            subject_code=subject.code,
            submitted_at=submission.submitted_at,
            marks=float(submission.marks) if submission.marks is not None else None,
            max_marks=float(assignment.max_marks),
            tab_switches=submission.tab_switches or 0,
        )
        for submission, assignment, subject in rows
    ]


def get_student_360(db: Session, faculty: User, student_id: int) -> Student360View:
    student, profile = _scoped_student(db, faculty, student_id)
    return Student360View(
        header=_header(db, student, profile),
        risk=_risk(db, student_id),
        metrics=_metrics(db, student_id),
        journey=_journey(db, student_id),
        doubts=_doubts(db, student_id),
        submissions=_submissions(db, student_id),
    )
