from datetime import datetime, time, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import student_portal as repository
from app.schemas.student_portal import (
    FeedbackGiven,
    FeedbackReceived,
    FacultyCourseFeedback,
    JourneyEvent,
    PersonalRisk,
    RiskFactor,
    StudentCourse,
    StudentDashboard,
    StudentJourney,
    StudentFeedbackResponse,
)


def _percentage(numerator: int | float, denominator: int | float) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator) * 100, 1)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _risk_factors(factors: dict[str, Any]) -> list[RiskFactor]:
    values: list[RiskFactor] = []
    attendance = factors.get("attendance_rate")
    if isinstance(attendance, (float, int)):
        values.append(
            RiskFactor(
                key="attendance",
                label="Attendance",
                observation=f"{round(float(attendance) * 100, 1)}% attendance",
                contribution=0.45 * max(0.0, 1 - float(attendance)),
            )
        )

    marks = factors.get("average_mark_rate")
    if isinstance(marks, (float, int)):
        values.append(
            RiskFactor(
                key="marks",
                label="Marks",
                observation=f"{round(float(marks) * 100, 1)}% average mark rate",
                contribution=0.40 * max(0.0, 1 - float(marks)),
            )
        )

    missed = factors.get("missed_submissions")
    if isinstance(missed, (float, int)):
        missed_count = int(missed)
        total = factors.get("total_submissions")
        missed_rate = (
            min(missed_count / int(total), 1.0)
            if isinstance(total, (float, int)) and total > 0
            else float(missed_count)
        )
        values.append(
            RiskFactor(
                key="submissions",
                label="Submissions",
                observation=(
                    f"{missed_count} missed submission{'s' if missed_count != 1 else ''}"
                ),
                contribution=0.15 * missed_rate,
            )
        )

    return sorted(values, key=lambda factor: factor.contribution, reverse=True)[:3]


def get_dashboard(db: Session, student: User) -> StudentDashboard:
    course_rows = repository.enrolled_courses(db, student.id)
    attendance = repository.attendance_totals(db, student.id)
    assessments = repository.assessment_totals(db, student.id)

    courses: list[StudentCourse] = []
    attended_total = 0
    attendance_total = 0
    marks_numerator = 0.0
    marks_denominator = 0.0
    for enrollment, course, faculty in course_rows:
        attended, sessions = attendance.get(course.id, (0, 0))
        score, maximum, completed, total = assessments.get(course.id, (None, None, 0, 0))
        course_marks = (
            _percentage(float(score), float(maximum))
            if score is not None and maximum is not None
            else None
        )
        courses.append(
            StudentCourse(
                course_id=course.id,
                code=course.code,
                name=course.name,
                credits=course.credits,
                faculty_id=faculty.id,
                faculty_name=faculty.full_name,
                attendance_percentage=_percentage(attended, sessions),
                marks_percentage=course_marks,
                completed_assessments=completed,
                total_assessments=total,
            )
        )
        attended_total += attended
        attendance_total += sessions
        if score is not None and maximum is not None:
            marks_numerator += float(score)
            marks_denominator += float(maximum)

    risk_score = repository.latest_risk_score(db, student.id)
    risk = None
    if risk_score is not None:
        risk = PersonalRisk(
            score=float(risk_score.score),
            level=risk_score.risk_level,
            computed_at=risk_score.computed_at,
            contributing_factors=_risk_factors(risk_score.contributing_factors or {}),
        )

    return StudentDashboard(
        attendance_percentage=_percentage(attended_total, attendance_total),
        marks_percentage=_percentage(marks_numerator, marks_denominator),
        enrolled_courses=len(courses),
        courses=courses,
        risk=risk,
    )


def get_journey(db: Session, student: User) -> StudentJourney:
    events: list[JourneyEvent] = []

    for enrollment, course, _faculty in repository.enrolled_courses(db, student.id):
        events.append(
            JourneyEvent(
                occurred_at=_as_utc(enrollment.enrolled_at),
                event_type="course",
                title=f"Enrolled in {course.name}",
                description=f"{course.code} · {enrollment.semester}",
            )
        )

    for attendance, course in repository.student_attendance(db, student.id):
        events.append(
            JourneyEvent(
                occurred_at=datetime.combine(attendance.class_date, time.min, timezone.utc),
                event_type="attendance",
                title=f"{attendance.status.title()} · {course.code}",
                description=f"{course.name} class on {attendance.class_date.isoformat()}.",
            )
        )

    for mark, assessment, course in repository.student_marks(db, student.id):
        due_date = mark.submitted_at or datetime.combine(
            assessment.due_date,
            time.min,
            timezone.utc,
        )
        state = "Submitted" if mark.is_submitted else "Missed"
        events.append(
            JourneyEvent(
                occurred_at=_as_utc(due_date),
                event_type="assessment",
                title=f"{state} · {assessment.title}",
                description=(
                    f"{course.code} · {float(mark.score):g} of "
                    f"{float(assessment.max_score):g} points."
                ),
            )
        )

    for intervention in repository.student_interventions(db, student.id):
        events.append(
            JourneyEvent(
                occurred_at=datetime.combine(intervention.start_date, time.min, timezone.utc),
                event_type="support",
                title=f"{intervention.intervention_type.replace('_', ' ').title()} · "
                f"{intervention.status.replace('_', ' ').title()}",
                description=intervention.description,
            )
        )

    for feedback, faculty, course in repository.received_feedback(db, student.id):
        events.append(
            JourneyEvent(
                occurred_at=_as_utc(feedback.created_at),
                event_type="feedback",
                title=f"Feedback from {faculty.full_name}",
                description=f"{course.code}: {feedback.message}" if course else feedback.message,
            )
        )

    return StudentJourney(
        events=sorted(events, key=lambda item: item.occurred_at, reverse=True)
    )


def get_feedback(db: Session, student: User) -> StudentFeedbackResponse:
    received = [
        FeedbackReceived(
            id=feedback.id,
            faculty_name=faculty.full_name,
            course_name=course.name if course else None,
            message=feedback.message,
            created_at=feedback.created_at,
        )
        for feedback, faculty, course in repository.received_feedback(db, student.id)
    ]
    submitted = [
        FeedbackGiven(
            id=feedback.id,
            faculty_name=faculty.full_name,
            course_name=course.name,
            rating=feedback.rating,
            comments=feedback.comments,
            submitted_at=feedback.submitted_at,
        )
        for feedback, faculty, course in repository.submitted_feedback(db, student.id)
    ]
    return StudentFeedbackResponse(received=received, submitted=submitted)


def submit_feedback(
    db: Session,
    student: User,
    payload: FacultyCourseFeedback,
) -> int:
    feedback = repository.create_course_feedback(
        db,
        student_id=student.id,
        faculty_id=payload.faculty_id,
        course_id=payload.course_id,
        rating=payload.rating,
        comments=payload.comments,
    )
    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected faculty member and course are not one of your enrolled courses.",
        )
    return feedback.id
