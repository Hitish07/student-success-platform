"""Placement services.

Faculty can add and list placements for students in their own subjects.
The principal gets aggregate trends only — no student identifiers.
"""

from collections import defaultdict
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Department,
    FacultySubject,
    Placement,
    StudentProfile,
    Subject,
    User,
)
from app.schemas.placements import (
    PlacementCreate,
    PlacementCreateResponse,
    PlacementTrend,
    PlacementTrendPoint,
    PlacementView,
)


TREND_MONTHS = 6
PLACEMENT_TREND_NOTE = (
    "Distinct students with an accepted or joined placement, by month of "
    "offer date."
)


def _faculty_subject_ids(db: Session, faculty: User) -> list[int]:
    return list(
        db.execute(
            select(FacultySubject.subject_id).where(FacultySubject.faculty_id == faculty.id)
        ).scalars().all()
    )


def _assert_student_in_scope(db: Session, faculty: User, student_id: int) -> User:
    student = db.get(User, student_id)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student_id))
    if student is None or student.role != "student" or profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    my_subjects = _faculty_subject_ids(db, faculty)
    if not my_subjects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    in_my_class = db.scalar(
        select(Subject.id)
        .where(Subject.id.in_(my_subjects))
        .where(Subject.department_id == profile.department_id)
        .where(Subject.year == profile.year)
        .where(Subject.semester == profile.semester)
    )
    if in_my_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return student


def _placement_view(placement: Placement, student: User) -> PlacementView:
    return PlacementView(
        id=placement.id,
        student_id=student.id,
        student_name=student.full_name,
        student_email=student.email,
        company=placement.company,
        role=placement.role,
        package_lpa=float(placement.package_lpa) if placement.package_lpa is not None else None,
        offer_date=placement.offer_date,
        status=placement.status,
        created_at=placement.created_at,
    )


def create_placement(
    db: Session,
    faculty: User,
    payload: PlacementCreate,
) -> PlacementCreateResponse:
    student = _assert_student_in_scope(db, faculty, payload.student_id)

    placement = Placement(
        student_id=student.id,
        company=payload.company,
        role=payload.role,
        package_lpa=payload.package_lpa,
        offer_date=payload.offer_date,
        status=payload.status,
    )
    db.add(placement)
    db.flush()
    db.add(
        AuditLog(
            actor_id=faculty.id,
            action="placement.created",
            entity_type="placement",
            entity_id=str(placement.id),
        )
    )
    db.commit()
    db.refresh(placement)
    return PlacementCreateResponse(id=placement.id, message="Placement recorded.")


def list_placements(db: Session, faculty: User) -> list[PlacementView]:
    my_subjects = _faculty_subject_ids(db, faculty)
    if not my_subjects:
        return []

    # Students in subjects the faculty teaches
    student_ids = list(
        db.execute(
            select(StudentProfile.user_id)
            .join(
                Subject,
                (Subject.department_id == StudentProfile.department_id)
                & (Subject.year == StudentProfile.year)
                & (Subject.semester == StudentProfile.semester),
            )
            .where(Subject.id.in_(my_subjects))
            .distinct()
        ).scalars().all()
    )
    if not student_ids:
        return []

    rows = db.execute(
        select(Placement, User)
        .join(User, User.id == Placement.student_id)
        .where(Placement.student_id.in_(student_ids))
        .order_by(Placement.offer_date.desc(), Placement.id.desc())
    ).all()
    return [_placement_view(placement, student) for placement, student in rows]


def _month_keys(count: int) -> list[str]:
    today = date.today()
    keys: list[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(keys))


def get_placement_trend(db: Session) -> PlacementTrend:
    keys = _month_keys(TREND_MONTHS)

    # Distinct placed students per month (offer_date), accepted/joined only
    rows = db.execute(
        select(Placement.student_id, Placement.offer_date, Placement.status)
        .where(Placement.status.in_(["accepted", "joined"]))
    ).all()

    buckets: dict[str, set[int]] = defaultdict(set)
    placed_students: set[int] = set()
    for student_id, offer_date, _status in rows:
        if offer_date is None:
            continue
        month_key = offer_date.strftime("%Y-%m")
        buckets[month_key].add(student_id)
        placed_students.add(student_id)

    points = [
        PlacementTrendPoint(label=key, value=float(len(buckets.get(key, set()))))
        for key in keys
    ]

    total_students = db.scalar(select(func.count()).select_from(StudentProfile)) or 0
    total_placed = len(placed_students)
    rate = (total_placed / int(total_students)) if total_students else 0.0

    return PlacementTrend(
        points=points,
        total_placed=total_placed,
        placement_rate=round(rate, 4),
        note=PLACEMENT_TREND_NOTE,
    )
