from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import AuthenticatedUser, DatabaseSession
from app.models import Department
from app.schemas.auth import (
    DepartmentResponse,
    LoginRequest,
    RefreshRequest,
    StudentRegistration,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate,
    list_departments as available_departments,
    register_student,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(db: DatabaseSession) -> list[Department]:
    return available_departments(db)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: StudentRegistration, db: DatabaseSession) -> dict:
    try:
        return register_student(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DatabaseSession) -> dict:
    return authenticate(db, str(payload.email), payload.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DatabaseSession) -> dict:
    return rotate_refresh_token(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    user: AuthenticatedUser,
    db: DatabaseSession,
) -> None:
    revoke_refresh_token(db, payload.refresh_token, user)


@router.get("/me", response_model=UserResponse)
def me(user: AuthenticatedUser) -> UserResponse:
    return user
