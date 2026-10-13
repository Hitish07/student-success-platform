from fastapi import APIRouter, Depends, status

from app.api.dependencies import AuthenticatedUser, DatabaseSession, require_roles
from app.schemas.faculty_portal import (
    AlertView,
    AssessmentCreate,
    AssessmentView,
    AtRiskStudent,
    AttendanceEntry,
    AttendanceUpdate,
    AttendanceView,
    CreatedResponse,
    FacultyDashboard,
    FacultyFeedbackView,
    FacultyStudent,
    InterventionCreate,
    InterventionView,
    MarkEntry,
    MarkUpdate,
    MarkView,
    StudentNoteCreate,
    StudentNoteUpdate,
    StudentNoteView,
    FacultyDoubtsView,
    SuccessResponse,
)
from app.schemas.assignments import (
    AssignmentCreate,
    FacultyAssignmentView,
    FacultySubjectView,
    GradeSubmission,
    SubjectStudentView,
    SubmissionGradingView,
)
from app.schemas.assignments import AttemptActivityView
from app.services import assignments as assignments_service
from app.services import faculty_portal as service
from app.services.doubts import get_faculty_doubt_summary

router = APIRouter(
    prefix="/faculty",
    tags=["faculty portal"],
    dependencies=[Depends(require_roles("faculty"))],
)


@router.get("/my-subjects", response_model=list[FacultySubjectView])
def faculty_subjects(user: AuthenticatedUser, db: DatabaseSession) -> list[FacultySubjectView]:
    return assignments_service.get_faculty_subjects(db, user)


@router.get(
    "/subjects/{subject_id}/students",
    response_model=list[SubjectStudentView],
)
def subject_students(
    subject_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[SubjectStudentView]:
    return assignments_service.get_subject_students(db, user, subject_id)


@router.post(
    "/assignments",
    response_model=FacultyAssignmentView,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: AssignmentCreate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> FacultyAssignmentView:
    return assignments_service.create_assignment(db, user, payload)


@router.get("/assignments", response_model=list[FacultyAssignmentView])
def faculty_assignments(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[FacultyAssignmentView]:
    return assignments_service.get_faculty_assignments(db, user)


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=list[SubmissionGradingView],
)
def assignment_submissions(
    assignment_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[SubmissionGradingView]:
    return assignments_service.get_assignment_submissions(db, user, assignment_id)


@router.put("/submissions/{submission_id}/grade", response_model=SubmissionGradingView)
def grade_assignment_submission(
    submission_id: int,
    payload: GradeSubmission,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> SubmissionGradingView:
    return assignments_service.grade_submission(db, user, submission_id, payload)


@router.get("/dashboard", response_model=FacultyDashboard)
def faculty_dashboard(user: AuthenticatedUser, db: DatabaseSession) -> FacultyDashboard:
    return service.get_dashboard(db, user)


@router.get("/courses/{course_id}/students", response_model=list[FacultyStudent])
def course_students(
    course_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[FacultyStudent]:
    return service.get_course_students(db, user, course_id)


@router.get("/courses/{course_id}/assessments", response_model=list[AssessmentView])
def course_assessments(
    course_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[AssessmentView]:
    return service.get_assessments(db, user, course_id)


@router.post(
    "/courses/{course_id}/assessments",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course_assessment(
    course_id: int,
    payload: AssessmentCreate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> CreatedResponse:
    return service.create_assessment(db, user, course_id, payload)


@router.get("/attendance", response_model=list[AttendanceView])
def faculty_attendance(user: AuthenticatedUser, db: DatabaseSession) -> list[AttendanceView]:
    return service.get_attendance(db, user)


@router.post(
    "/attendance",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance(
    payload: AttendanceEntry,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> CreatedResponse:
    return service.create_attendance(db, user, payload)


@router.put("/attendance/{attendance_id}", response_model=SuccessResponse)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> SuccessResponse:
    return service.update_attendance(db, user, attendance_id, payload)


@router.get("/courses/{course_id}/marks", response_model=list[MarkView])
def course_marks(
    course_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[MarkView]:
    return service.get_course_marks(db, user, course_id)


@router.post("/marks", response_model=CreatedResponse, status_code=status.HTTP_201_CREATED)
def create_mark(
    payload: MarkEntry,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> CreatedResponse:
    return service.create_mark(db, user, payload)


@router.put("/marks/{mark_id}", response_model=SuccessResponse)
def update_mark(
    mark_id: int,
    payload: MarkUpdate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> SuccessResponse:
    return service.update_mark(db, user, mark_id, payload)


@router.get("/students/{student_id}/notes", response_model=list[StudentNoteView])
def student_notes(
    student_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[StudentNoteView]:
    return service.get_student_notes(db, user, student_id)


@router.post("/notes", response_model=CreatedResponse, status_code=status.HTTP_201_CREATED)
def create_student_note(
    payload: StudentNoteCreate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> CreatedResponse:
    return service.create_student_note(db, user, payload)


@router.put("/notes/{note_id}", response_model=SuccessResponse)
def update_student_note(
    note_id: int,
    payload: StudentNoteUpdate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> SuccessResponse:
    return service.update_student_note(db, user, note_id, payload)


@router.get(
    "/students/{student_id}/interventions",
    response_model=list[InterventionView],
)
def student_interventions(
    student_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[InterventionView]:
    return service.get_student_interventions(db, user, student_id)


@router.post(
    "/interventions",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_intervention(
    payload: InterventionCreate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> CreatedResponse:
    return service.create_intervention(db, user, payload)


@router.get("/at-risk", response_model=list[AtRiskStudent])
def at_risk_students(user: AuthenticatedUser, db: DatabaseSession) -> list[AtRiskStudent]:
    return service.get_at_risk_students(db, user)


@router.get("/alerts", response_model=list[AlertView])
def faculty_alerts(user: AuthenticatedUser, db: DatabaseSession) -> list[AlertView]:
    return service.get_faculty_alerts(db, user)


@router.get("/feedback", response_model=list[FacultyFeedbackView])
def faculty_feedback(user: AuthenticatedUser, db: DatabaseSession) -> list[FacultyFeedbackView]:
    return service.get_faculty_feedback(db, user)


@router.get(
    "/assignments/{assignment_id}/attempts",
    response_model=list[AttemptActivityView],
)
def assignment_attempts(
    assignment_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[AttemptActivityView]:
    return assignments_service.get_assignment_attempts(db, user, assignment_id)


@router.get("/doubts", response_model=FacultyDoubtsView)
def faculty_doubts(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> FacultyDoubtsView:
    return get_faculty_doubt_summary(db, user)
