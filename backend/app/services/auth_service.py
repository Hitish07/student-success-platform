from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import (
    AuthRefreshToken,
    Department,
    FacultyProfile,
    FacultySubject,
    StudentProfile,
    Subject,
    User,
)
from app.schemas.auth import FacultyRegistration, StudentRegistration

VALID_ROLES = {"student", "faculty", "dean", "principal"}


def list_departments(db: Session) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.name)).all())


def list_department_subjects(db: Session, department_id: int) -> list[Subject]:
    return list(
        db.scalars(
            select(Subject)
            .where(Subject.department_id == department_id)
            .order_by(Subject.year, Subject.semester, Subject.code)
        ).all()
    )


def public_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "department_id": user.department_id,
    }


def _issue_token_pair(db: Session, user: User) -> dict[str, Any]:
    access_token, _, _ = create_token(
        user_id=user.id,
        role=user.role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token, refresh_jti, refresh_expires_at = create_token(
        user_id=user.id,
        role=user.role,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(
        AuthRefreshToken(
            jti=refresh_jti,
            user_id=user.id,
            expires_at=refresh_expires_at,
        )
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": public_user(user),
    }


def register_student(db: Session, payload: StudentRegistration) -> dict[str, Any]:
    department = db.get(Department, payload.department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select a valid department.")

    user = User(
        email=str(payload.email).strip().lower(),
        full_name=payload.full_name,
        role="student",
        department_id=department.id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(
        StudentProfile(
            user_id=user.id,
            department_id=department.id,
            year=payload.year,
            semester=payload.semester,
        )
    )
    token_pair = _issue_token_pair(db, user)
    db.commit()
    return token_pair


def register_faculty(db: Session, payload: FacultyRegistration) -> dict[str, Any]:
    department = db.get(Department, payload.department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select a valid department.")

    subjects = list(
        db.scalars(
            select(Subject).where(
                Subject.id.in_(payload.subject_ids),
                Subject.department_id == department.id,
            )
        ).all()
    )
    if len(subjects) != len(payload.subject_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Every selected subject must belong to the selected department.",
        )

    user = User(
        email=str(payload.email).strip().lower(),
        full_name=payload.name,
        role="faculty",
        department_id=department.id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(FacultyProfile(user_id=user.id, department_id=department.id))
    db.add_all(
        FacultySubject(faculty_id=user.id, subject_id=subject.id)
        for subject in subjects
    )
    token_pair = _issue_token_pair(db, user)
    db.commit()
    return token_pair


def authenticate(db: Session, email: str, password: str) -> dict[str, Any]:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is inactive.")

    token_pair = _issue_token_pair(db, user)
    db.commit()
    return token_pair


def _decode_user_claims(token: str, expected_type: str) -> tuple[dict[str, Any], int]:
    try:
        claims = decode_token(token, expected_type)
        user_id = int(claims["sub"])
        UUID(str(claims["jti"]))
        if claims["role"] not in VALID_ROLES:
            raise jwt.InvalidTokenError("Unknown role.")
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return claims, user_id


def current_user_from_access_token(db: Session, token: str) -> User:
    claims, user_id = _decode_user_claims(token, "access")
    user = db.get(User, user_id)
    if user is None or not user.is_active or claims["role"] != user.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def rotate_refresh_token(db: Session, token: str) -> dict[str, Any]:
    claims, user_id = _decode_user_claims(token, "refresh")
    user = db.get(User, user_id)
    if user is None or not user.is_active or claims["role"] != user.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    now = datetime.now(timezone.utc)
    result = db.execute(
        update(AuthRefreshToken)
        .where(
            AuthRefreshToken.jti == claims["jti"],
            AuthRefreshToken.user_id == user_id,
            AuthRefreshToken.revoked_at.is_(None),
            AuthRefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    token_pair = _issue_token_pair(db, user)
    db.commit()
    return token_pair


def revoke_refresh_token(db: Session, token: str, authenticated_user: User) -> None:
    claims, user_id = _decode_user_claims(token, "refresh")
    if user_id != authenticated_user.id or claims["role"] != authenticated_user.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    db.execute(
        update(AuthRefreshToken)
        .where(
            AuthRefreshToken.jti == claims["jti"],
            AuthRefreshToken.user_id == authenticated_user.id,
            AuthRefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
