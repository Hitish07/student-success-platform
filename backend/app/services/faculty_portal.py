from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Assessment,
    Attendance,
    AuditLog,
    Course,
    Enrollment,
    Intervention,
    Mark,
    RiskScore,
    StudentNote,
    User,
)
from app.repositories import faculty_portal as repository
from app.schemas.faculty_portal import (
    AlertView,
    AssessmentCreate,
    AssessmentView,
    AtRiskStudent,
    AttendanceEntry,
    AttendanceUpdate,
    AttendanceView,
    CreatedResponse,
    FacultyCourse,
    FacultyDashboard,
    FacultyFeedbackView,
    FacultyStudent,
    InterventionCreate,
    InterventionView,
    MarkEntry,
    MarkUpdate,
    MarkView,
    RiskFactorView,
    StudentNoteCreate,
    StudentNoteUpdate,
    StudentNoteView,
    SuccessResponse,
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")


def _bad_date(value: date) -> None:
    if value > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dates cannot be in the future.",
        )


def _audit(db: Session, faculty: User, action: str, entity: str, entity_id: int) -> None:
    db.add(
        AuditLog(
            actor_id=faculty.id,
            action=action,
            entity_type=entity,
            entity_id=str(entity_id),
        )
    )


def _commit(db: Session, *, conflict_detail: str = "The record conflicts with existing data.") -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail) from exc


def _flush(db: Session, conflict_detail: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail) from exc


def get_dashboard(db: Session, faculty: User) -> FacultyDashboard:
    course_rows = repository.faculty_courses(db, faculty.id)
    student_ids = repository.assigned_student_ids(db, faculty.id)
    risk_rows = repository.latest_risks(db, faculty.id, student_ids)
    return FacultyDashboard(
        courses=[
            FacultyCourse(
                id=course.id,
                code=course.code,
                name=course.name,
                credits=course.credits,
                enrolled_students=count,
            )
            for course, count in course_rows
        ],
        assigned_students=len(student_ids),
        at_risk_students=sum(1 for risk, _student in risk_rows if risk.risk_level in ("medium", "high")),
        open_alerts=sum(repository.open_alert_counts(db, student_ids).values()),
    )


def get_course_students(db: Session, faculty: User, course_id: int) -> list[FacultyStudent]:
    if not repository.course_is_assigned(db, faculty.id, course_id):
        raise _not_found()
    students = repository.students_for_course(db, faculty.id, course_id)
    attendance, marks = repository.student_progress(
        db,
        faculty.id,
        course_id,
        [student.id for student in students],
    )
    risk_by_student = {
        student.id: risk
        for risk, student in repository.latest_risks(
            db,
            faculty.id,
            [student.id for student in students],
        )
    }
    result = []
    for student in students:
        present, total = attendance.get(student.id, (0, 0))
        score, maximum = marks.get(student.id, (0.0, 0.0))
        risk = risk_by_student.get(student.id)
        result.append(
            FacultyStudent(
                id=student.id,
                full_name=student.full_name,
                email=student.email,
                attendance_percentage=round(present / total * 100, 1) if total else None,
                marks_percentage=round(score / maximum * 100, 1) if maximum else None,
                latest_risk_level=risk.risk_level if risk else None,
            )
        )
    return result


def get_assessments(db: Session, faculty: User, course_id: int) -> list[AssessmentView]:
    if not repository.course_is_assigned(db, faculty.id, course_id):
        raise _not_found()
    return [
        AssessmentView(
            id=item.id,
            course_id=item.course_id,
            title=item.title,
            assessment_type=item.assessment_type,
            max_score=item.max_score,
            due_date=item.due_date,
        )
        for item in repository.assigned_assessments(db, faculty.id, course_id)
    ]


def create_assessment(
    db: Session,
    faculty: User,
    course_id: int,
    payload: AssessmentCreate,
) -> CreatedResponse:
    if not repository.course_is_assigned(db, faculty.id, course_id):
        raise _not_found()
    assessment = Assessment(
        course_id=course_id,
        title=payload.title,
        assessment_type=payload.assessment_type,
        max_score=payload.max_score,
        due_date=payload.due_date,
    )
    db.add(assessment)
    _flush(db, "The assessment conflicts with existing data.")
    _commit(db)
    db.refresh(assessment)
    return CreatedResponse(id=assessment.id)


def get_attendance(db: Session, faculty: User) -> list[AttendanceView]:
    return [
        AttendanceView(
            id=attendance.id,
            student_id=student.id,
            student_name=student.full_name,
            course_id=course.id,
            course_code=course.code,
            class_date=attendance.class_date,
            status=attendance.status,
        )
        for attendance, student, course in repository.attendance_for_faculty(db, faculty.id)
    ]


def create_attendance(
    db: Session,
    faculty: User,
    payload: AttendanceEntry,
) -> CreatedResponse:
    _bad_date(payload.class_date)
    if not repository.student_is_enrolled(
        db, faculty.id, payload.course_id, payload.student_id
    ):
        raise _not_found()
    duplicate = db.scalar(
        select(Attendance.id).where(
            Attendance.student_id == payload.student_id,
            Attendance.course_id == payload.course_id,
            Attendance.class_date == payload.class_date,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance already exists for this student, course, and date.",
        )
    attendance = Attendance(
        student_id=payload.student_id,
        course_id=payload.course_id,
        class_date=payload.class_date,
        status=payload.status,
    )
    db.add(attendance)
    _flush(db, "Attendance already exists for this student, course, and date.")
    _audit(db, faculty, "attendance.created", "attendance", attendance.id)
    _commit(db, conflict_detail="Attendance already exists for this student, course, and date.")
    return CreatedResponse(id=attendance.id)


def update_attendance(
    db: Session,
    faculty: User,
    attendance_id: int,
    payload: AttendanceUpdate,
) -> SuccessResponse:
    _bad_date(payload.class_date)
    attendance = repository.attendance_record(db, faculty.id, attendance_id)
    if attendance is None:
        raise _not_found()
    attendance.class_date = payload.class_date
    attendance.status = payload.status
    _audit(db, faculty, "attendance.updated", "attendance", attendance.id)
    _commit(db)
    return SuccessResponse(id=attendance.id, message="Saved.")


def get_course_marks(db: Session, faculty: User, course_id: int) -> list[MarkView]:
    if not repository.course_is_assigned(db, faculty.id, course_id):
        raise _not_found()
    return [
        MarkView(
            id=mark.id,
            student_id=student.id,
            student_name=student.full_name,
            assessment_id=assessment.id,
            assessment_title=assessment.title,
            max_score=assessment.max_score,
            score=mark.score,
            is_submitted=mark.is_submitted,
            submitted_at=mark.submitted_at,
        )
        for mark, student, assessment in repository.marks_for_course(db, faculty.id, course_id)
    ]


def create_mark(db: Session, faculty: User, payload: MarkEntry) -> CreatedResponse:
    assessment = repository.assessment_for_faculty(db, faculty.id, payload.assessment_id)
    if assessment is None or not repository.student_is_enrolled(
        db, faculty.id, assessment.course_id, payload.student_id
    ):
        raise _not_found()
    if payload.score > assessment.max_score:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Score cannot exceed the assessment maximum.",
        )
    mark = Mark(
        student_id=payload.student_id,
        assessment_id=assessment.id,
        score=payload.score,
        is_submitted=payload.is_submitted,
        submitted_at=datetime.now(timezone.utc) if payload.is_submitted else None,
    )
    db.add(mark)
    _flush(db, "A mark already exists for this student and assessment.")
    _audit(db, faculty, "mark.created", "mark", mark.id)
    _commit(db, conflict_detail="A mark already exists for this student and assessment.")
    return CreatedResponse(id=mark.id)


def update_mark(
    db: Session,
    faculty: User,
    mark_id: int,
    payload: MarkUpdate,
) -> SuccessResponse:
    mark = repository.mark_record(db, faculty.id, mark_id)
    if mark is None:
        raise _not_found()
    assessment = db.get(Assessment, mark.assessment_id)
    if assessment is None or payload.score > assessment.max_score:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Score cannot exceed the assessment maximum.",
        )
    mark.score = payload.score
    mark.is_submitted = payload.is_submitted
    mark.submitted_at = datetime.now(timezone.utc) if payload.is_submitted else None
    _audit(db, faculty, "mark.updated", "mark", mark.id)
    _commit(db)
    return SuccessResponse(id=mark.id, message="Saved.")


def get_student_notes(
    db: Session,
    faculty: User,
    student_id: int,
) -> list[StudentNoteView]:
    if not repository.student_is_assigned(db, faculty.id, student_id):
        raise _not_found()
    return [
        StudentNoteView(
            id=note.id,
            student_id=note.student_id,
            author_id=note.author_id,
            author_name=author.full_name,
            content=note.content,
            created_at=note.created_at,
        )
        for note, author in repository.notes_for_student(db, faculty.id, student_id)
    ]


def create_student_note(
    db: Session,
    faculty: User,
    payload: StudentNoteCreate,
) -> CreatedResponse:
    if not repository.student_is_assigned(db, faculty.id, payload.student_id):
        raise _not_found()
    note = StudentNote(
        student_id=payload.student_id,
        author_id=faculty.id,
        content=payload.content,
    )
    db.add(note)
    _flush(db, "The note conflicts with existing data.")
    _audit(db, faculty, "student_note.created", "student_note", note.id)
    db.commit()
    db.refresh(note)
    return CreatedResponse(id=note.id)


def update_student_note(
    db: Session,
    faculty: User,
    note_id: int,
    payload: StudentNoteUpdate,
) -> SuccessResponse:
    note = repository.note_record(db, faculty.id, note_id)
    if note is None:
        raise _not_found()
    note.content = payload.content
    _audit(db, faculty, "student_note.updated", "student_note", note.id)
    db.commit()
    return SuccessResponse(id=note.id, message="Saved.")


def get_student_interventions(
    db: Session,
    faculty: User,
    student_id: int,
) -> list[InterventionView]:
    if not repository.student_is_assigned(db, faculty.id, student_id):
        raise _not_found()
    return [
        InterventionView(
            id=item.id,
            student_id=item.student_id,
            intervention_type=item.intervention_type,
            description=item.description,
            start_date=item.start_date,
            status=item.status,
        )
        for item in repository.interventions_for_student(db, faculty.id, student_id)
    ]


def create_intervention(
    db: Session,
    faculty: User,
    payload: InterventionCreate,
) -> CreatedResponse:
    _bad_date(payload.start_date)
    if not repository.student_is_assigned(db, faculty.id, payload.student_id):
        raise _not_found()
    item = Intervention(
        student_id=payload.student_id,
        assigned_by=faculty.id,
        intervention_type=payload.intervention_type,
        description=payload.description,
        start_date=payload.start_date,
        status="assigned",
    )
    db.add(item)
    _flush(db, "The intervention conflicts with existing data.")
    _audit(db, faculty, "intervention.created", "intervention", item.id)
    db.commit()
    db.refresh(item)
    return CreatedResponse(id=item.id)


def get_at_risk_students(db: Session, faculty: User) -> list[AtRiskStudent]:
    student_ids = repository.assigned_student_ids(db, faculty.id)
    alert_counts = repository.open_alert_counts(db, student_ids)
    result: list[AtRiskStudent] = []
    for risk, student in repository.latest_risks(db, faculty.id, student_ids):
        if risk.risk_level not in ("medium", "high"):
            continue
        result.append(
            AtRiskStudent(
                student_id=student.id,
                student_name=student.full_name,
                course_codes=repository.student_course_codes(db, faculty.id, student.id),
                risk_score=float(risk.score),
                risk_level=risk.risk_level,
                contributing_factors=[
                    RiskFactorView(key=str(key), observation=_risk_observation(str(key), value))
                    for key, value in (risk.contributing_factors or {}).items()
                    if key != "total_submissions"
                ],
                open_alerts=alert_counts.get(student.id, 0),
            )
        )
    return sorted(result, key=lambda item: (-item.risk_score, item.student_name))


def _risk_observation(key: str, value: object) -> str:
    if key == "attendance_rate" and isinstance(value, (int, float)):
        return f"{round(value * 100, 1)}% attendance"
    if key == "average_mark_rate" and isinstance(value, (int, float)):
        return f"{round(value * 100, 1)}% average mark rate"
    if key == "missed_submissions" and isinstance(value, (int, float)):
        count = int(value)
        return f"{count} missed submission{'s' if count != 1 else ''}"
    return str(value)


def get_faculty_alerts(db: Session, faculty: User) -> list[AlertView]:
    return [
        AlertView(
            id=alert.id,
            student_id=student.id,
            student_name=student.full_name,
            course_codes=repository.student_course_codes(db, faculty.id, student.id),
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            created_at=alert.created_at,
        )
        for alert, student in repository.alerts_for_faculty(db, faculty.id)
    ]


def get_faculty_feedback(db: Session, faculty: User) -> list[FacultyFeedbackView]:
    return [
        FacultyFeedbackView(
            id=feedback.id,
            student_name=student.full_name,
            course_name=course.name if course else None,
            rating=feedback.rating,
            comments=feedback.comments,
            submitted_at=feedback.submitted_at,
        )
        for feedback, student, course in repository.feedback_for_faculty(db, faculty.id)
    ]
