from fastapi import APIRouter, Depends, status

from app.api.dependencies import AuthenticatedUser, DatabaseSession, require_roles
from app.models import User
from app.schemas.student_portal import (
    FacultyCourseFeedback,
    FeedbackSubmission,
    StudentDashboard,
    StudentFeedbackResponse,
    StudentJourney,
)
from app.services.student_portal import (
    get_dashboard,
    get_feedback,
    get_journey,
    submit_feedback,
)

router = APIRouter(
    prefix="/student",
    tags=["student portal"],
    dependencies=[Depends(require_roles("student"))],
)


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
