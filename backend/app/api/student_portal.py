from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import AuthenticatedUser, DatabaseSession, require_roles
from app.models import User
from app.schemas.student_portal import (
    FacultyCourseFeedback,
    FeedbackSubmission,
    StudentDashboard,
    StudentAcademicProfile,
    StudentAcademicProfileUpdate,
    StudentFeedbackResponse,
    StudentJourney,
    StudentSubjects,
)
from app.schemas.assignments import (
    AssignmentSubmissionView,
    AssignmentSubmit,
    AttemptView,
    StudentAssignmentView,
)
from app.schemas.doubts import DoubtAsk, DoubtList, DoubtView
from app.services.assignments import (
    get_student_assignments,
    record_tab_switch,
    start_attempt,
    submit_assignment,
)
from app.services.doubts import ask_doubt, list_doubts
from app.services.student_portal import (
    get_academic_profile,
    get_academic_subjects,
    get_dashboard,
    get_feedback,
    get_journey,
    submit_feedback,
    update_academic_profile,
)

router = APIRouter(
    prefix="/student",
    tags=["student portal"],
    dependencies=[Depends(require_roles("student"))],
)


@router.get("/assignments", response_model=list[StudentAssignmentView])
def student_assignments(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> list[StudentAssignmentView]:
    return get_student_assignments(db, user)


@router.post(
    "/assignments/{assignment_id}/submit",
    response_model=AssignmentSubmissionView,
    status_code=status.HTTP_201_CREATED,
)
def submit_student_assignment(
    assignment_id: int,
    payload: AssignmentSubmit,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> AssignmentSubmissionView:
    return submit_assignment(db, user, assignment_id, payload)


@router.get("/profile", response_model=StudentAcademicProfile)
def student_profile(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> StudentAcademicProfile:
    return get_academic_profile(db, user)


@router.put("/profile", response_model=StudentAcademicProfile)
def update_student_profile(
    payload: StudentAcademicProfileUpdate,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> StudentAcademicProfile:
    return update_academic_profile(db, user, payload)


@router.get("/subjects", response_model=StudentSubjects)
def student_subjects(
    user: AuthenticatedUser,
    db: DatabaseSession,
    year: int | None = Query(default=None, ge=1, le=4),
    semester: int | None = Query(default=None, ge=1, le=2),
) -> StudentSubjects:
    return get_academic_subjects(db, user, year, semester)


@router.get("/dashboard", response_model=StudentDashboard)
def student_dashboard(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> StudentDashboard:
    return get_dashboard(db, user)


@router.get("/journey", response_model=StudentJourney)
def student_journey(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> StudentJourney:
    return get_journey(db, user)


@router.get("/feedback", response_model=StudentFeedbackResponse)
def student_feedback(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> StudentFeedbackResponse:
    return get_feedback(db, user)


@router.post(
    "/feedback",
    response_model=FeedbackSubmission,
    status_code=status.HTTP_201_CREATED,
)
def create_student_feedback(
    payload: FacultyCourseFeedback,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> FeedbackSubmission:
    feedback_id = submit_feedback(db, user, payload)
    return FeedbackSubmission(id=feedback_id, message="Feedback submitted.")


@router.post(
    "/assignments/{assignment_id}/attempt",
    response_model=AttemptView,
)
def start_assignment_attempt(
    assignment_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> AttemptView:
    return start_attempt(db, user, assignment_id)


@router.post(
    "/assignments/{assignment_id}/tab-switch",
    response_model=AttemptView,
)
def report_assignment_tab_switch(
    assignment_id: int,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> AttemptView:
    return record_tab_switch(db, user, assignment_id)


@router.get("/doubts", response_model=DoubtList)
def student_doubts(
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> DoubtList:
    return list_doubts(db, user)


@router.post(
    "/doubts",
    response_model=DoubtView,
    status_code=status.HTTP_201_CREATED,
)
def create_student_doubt(
    payload: DoubtAsk,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> DoubtView:
    return ask_doubt(db, user, payload)
