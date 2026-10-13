from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser, DatabaseSession, require_roles
from app.models import User
from app.schemas.data_integration import DataIntegrationResult
from app.schemas.success_analytics import (
    RiskFlagsResponse,
    SegmentsResponse,
    StudentRiskFlags,
    StudentSuccessScore,
    SuccessScoresResponse,
)
from app.services.data_integration import build_data_integration
from app.services.success_analytics import score_students, segment_students

router = APIRouter(
    prefix="/analytics",
    tags=["data integration"],
)


@router.get("/data-integration", response_model=DataIntegrationResult)
def get_data_integration(
    user: Annotated[User, Depends(require_roles("dean", "principal"))],
    db: DatabaseSession,
) -> DataIntegrationResult:
    if user.role == "dean" and user.department_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A department assignment is required for this report.",
        )
    department_id = user.department_id if user.role == "dean" else None
    return build_data_integration(db, department_id)


def _scoped_scores(db: Session, user: User) -> list[StudentSuccessScore]:
    if user.role == "dean" and user.department_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A department assignment is required for this report.",
        )
    department_id = user.department_id if user.role == "dean" else None
    integrated = build_data_integration(db, department_id)
    return score_students(integrated.students)


@router.get("/success-scores", response_model=SuccessScoresResponse)
def get_success_scores(
    user: Annotated[User, Depends(require_roles("dean", "principal"))],
    db: DatabaseSession,
) -> SuccessScoresResponse:
    return SuccessScoresResponse(students=_scoped_scores(db, user))


@router.get("/risk-flags", response_model=RiskFlagsResponse)
def get_risk_flags(
    user: Annotated[User, Depends(require_roles("dean", "principal"))],
    db: DatabaseSession,
) -> RiskFlagsResponse:
    return RiskFlagsResponse(
        students=[
            StudentRiskFlags(
                student_id=score.student_id,
                student_name=score.student_name,
                department=score.department,
                cohort=score.cohort,
                academic_risk=score.academic_risk,
                placement_risk=score.placement_risk,
            )
            for score in _scoped_scores(db, user)
        ]
    )


@router.get("/segments", response_model=SegmentsResponse)
def get_student_segments(
    user: Annotated[User, Depends(require_roles("dean", "principal"))],
    db: DatabaseSession,
) -> SegmentsResponse:
    segments = segment_students(_scoped_scores(db, user))
    counts: dict[str, int] = {}
    for student in segments:
        counts[student.segment] = counts.get(student.segment, 0) + 1
    return SegmentsResponse(students=segments, segment_counts=counts)
