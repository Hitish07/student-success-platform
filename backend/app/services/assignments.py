from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    AssignmentSubmission,
    AuditLog,
    FacultySubject,
    StudentProfile,
    Subject,
    User,
)
from app.schemas.assignments import (
    AssignmentCreate,
    AssignmentSubmit,
    AssignmentSubmissionView,
    FacultyAssignmentView,
    FacultySubjectView,
    GradeSubmission,
    StudentAssignmentView,
    SubjectStudentView,
    SubmissionGradingView,
)


def get_faculty_subjects(db: Session, faculty: User) -> list[FacultySubjectView]:
    rows = db.execute(
        select(Subject)
        .join(FacultySubject, FacultySubject.subject_id == Subject.id)
        .where(FacultySubject.faculty_id == faculty.id)
        .order_by(Subject.year, Subject.semester, Subject.code)
    ).scalars()
    return [
        FacultySubjectView(
            id=subject.id,
            code=subject.code,
            name=subject.name,
            year=subject.year,
            semester=subject.semester,
        )
        for subject in rows
    ]


def get_subject_students(db: Session, faculty: User, subject_id: int) -> list[SubjectStudentView]:
    subject = db.get(Subject, subject_id)
    is_taught = db.scalar(
        select(FacultySubject.id).where(
            FacultySubject.faculty_id == faculty.id,
            FacultySubject.subject_id == subject_id,
        )
    )
    if subject is None or is_taught is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    students = db.execute(
        select(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .where(
            User.role == "student",
            StudentProfile.department_id == subject.department_id,
            StudentProfile.year == subject.year,
            StudentProfile.semester == subject.semester,
        )
        .order_by(User.full_name, User.id)
    ).scalars()
    return [
        SubjectStudentView(id=student.id, full_name=student.full_name, email=student.email)
        for student in students
    ]


def _faculty_assignment_view(assignment: Assignment, subject: Subject) -> FacultyAssignmentView:
    return FacultyAssignmentView(
        id=assignment.id,
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        max_marks=assignment.max_marks,
        created_at=assignment.created_at,
    )


def create_assignment(
    db: Session,
    faculty: User,
    payload: AssignmentCreate,
) -> FacultyAssignmentView:
    subject = db.get(Subject, payload.subject_id)
    is_taught = db.scalar(
        select(FacultySubject.id).where(
            FacultySubject.faculty_id == faculty.id,
            FacultySubject.subject_id == payload.subject_id,
        )
    )
    if subject is None or is_taught is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    assignment = Assignment(
        subject_id=subject.id,
        faculty_id=faculty.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        max_marks=payload.max_marks,
    )
    db.add(assignment)
    db.flush()
    db.add(
        AuditLog(
            actor_id=faculty.id,
            action="assignment.created",
            entity_type="assignment",
            entity_id=str(assignment.id),
        )
    )
    db.commit()
    db.refresh(assignment)
    return _faculty_assignment_view(assignment, subject)


def get_faculty_assignments(db: Session, faculty: User) -> list[FacultyAssignmentView]:
    rows = db.execute(
        select(Assignment, Subject)
        .join(Subject, Subject.id == Assignment.subject_id)
        .where(Assignment.faculty_id == faculty.id)
        .order_by(Assignment.due_date, Assignment.id)
    ).all()
    return [_faculty_assignment_view(assignment, subject) for assignment, subject in rows]


def _student_profile(db: Session, student: User) -> StudentProfile:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student.id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student academic profile not found.",
        )
    return profile


def get_student_assignments(db: Session, student: User) -> list[StudentAssignmentView]:
    profile = _student_profile(db, student)
    rows = db.execute(
        select(Assignment, Subject, AssignmentSubmission)
        .join(Subject, Subject.id == Assignment.subject_id)
        .outerjoin(
            AssignmentSubmission,
            (AssignmentSubmission.assignment_id == Assignment.id)
            & (AssignmentSubmission.student_id == student.id),
        )
        .where(
            Subject.department_id == profile.department_id,
            Subject.year == profile.year,
            Subject.semester == profile.semester,
        )
        .order_by(Assignment.due_date, Assignment.id)
    ).all()

    results: list[StudentAssignmentView] = []
    for assignment, subject, submission in rows:
        submission_status = (
            "submitted"
            if submission is not None
            else "overdue"
            if assignment.due_date < date.today()
            else "open"
        )
        results.append(
            StudentAssignmentView(
                id=assignment.id,
                subject_id=subject.id,
                subject_code=subject.code,
                subject_name=subject.name,
                title=assignment.title,
                description=assignment.description,
                due_date=assignment.due_date,
                max_marks=assignment.max_marks,
                status=submission_status,
                submitted_at=submission.submitted_at if submission is not None else None,
                answer_text=submission.answer_text if submission is not None else None,
                marks=submission.marks if submission is not None else None,
                feedback=submission.feedback if submission is not None else None,
            )
        )
    return results


def submit_assignment(
    db: Session,
    student: User,
    assignment_id: int,
    payload: AssignmentSubmit,
) -> AssignmentSubmissionView:
    profile = _student_profile(db, student)
    assignment = db.get(Assignment, assignment_id)
    subject = db.get(Subject, assignment.subject_id) if assignment is not None else None
    if (
        assignment is None
        or subject is None
        or subject.department_id != profile.department_id
        or subject.year != profile.year
        or subject.semester != profile.semester
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    existing = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == student.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment already submitted.")

    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=student.id,
        answer_text=payload.answer_text,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return AssignmentSubmissionView(
        id=submission.id,
        assignment_id=submission.assignment_id,
        submitted_at=submission.submitted_at,
    )


def _grading_view(
    submission: AssignmentSubmission,
    assignment: Assignment,
    student: User,
) -> SubmissionGradingView:
    return SubmissionGradingView(
        id=submission.id,
        assignment_id=assignment.id,
        student_id=student.id,
        student_name=student.full_name,
        student_email=student.email,
        submitted_at=submission.submitted_at,
        answer_text=submission.answer_text,
        marks=submission.marks,
        feedback=submission.feedback,
        max_marks=assignment.max_marks,
    )


def get_assignment_submissions(
    db: Session,
    faculty: User,
    assignment_id: int,
) -> list[SubmissionGradingView]:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    rows = db.execute(
        select(AssignmentSubmission, User)
        .join(User, User.id == AssignmentSubmission.student_id)
        .where(AssignmentSubmission.assignment_id == assignment.id)
        .order_by(AssignmentSubmission.submitted_at, AssignmentSubmission.id)
    ).all()
    return [_grading_view(submission, assignment, student) for submission, student in rows]


def grade_submission(
    db: Session,
    faculty: User,
    submission_id: int,
    payload: GradeSubmission,
) -> SubmissionGradingView:
    submission = db.get(AssignmentSubmission, submission_id)
    assignment = db.get(Assignment, submission.assignment_id) if submission is not None else None
    if submission is None or assignment is None or assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    if payload.marks > assignment.max_marks:
        raise HTTPException(
            status_code=422,
            detail=f"Marks cannot exceed the maximum of {assignment.max_marks}.",
        )
    submission.marks = payload.marks
    submission.feedback = (payload.feedback or "").strip() or None
    db.add(
        AuditLog(
            actor_id=faculty.id,
            action="submission.graded",
            entity_type="assignment_submission",
            entity_id=str(submission.id),
        )
    )
    db.commit()
    db.refresh(submission)
    student = db.get(User, submission.student_id)
    return _grading_view(submission, assignment, student)
