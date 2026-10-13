from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import AuthenticatedUser, DatabaseSession
from app.models import Department, Subject
from app.schemas.auth import (
    DepartmentResponse,
    FacultyRegistration,
    LoginRequest,
    RefreshRequest,
    SubjectOptionResponse,
    StudentRegistration,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate,
    list_departments as available_departments,
    list_department_subjects,
    register_faculty,
    register_student,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/departments", response_model=list[DepartmentResponse])
def list_departments(db: DatabaseSession) -> list[Department]:
    return available_departments(db)


@router.get("/subjects", response_model=list[SubjectOptionResponse])
def list_subjects(
    db: DatabaseSession,
    department_id: int,
) -> list[Subject]:
    return list_department_subjects(db, department_id)


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


@router.post("/register/faculty", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_faculty_account(payload: FacultyRegistration, db: DatabaseSession) -> dict:
    try:
        return register_faculty(db, payload)
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
