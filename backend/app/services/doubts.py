"""Student doubts agent: ask, validate, store, list.

The agent never returns final code or a full answer. Two layers of enforcement:

1. The system instruction in `app.services.gemini` tells the model not to.
2. This module scans each reply for code fences and code-shaped patterns. If it
   finds any, it asks the model once more with a stricter instruction. If the
   second reply still contains code, the student gets a short fallback message
   instead of the reply.
"""

import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, StudentDoubt, StudentProfile, Subject, User
from app.schemas.doubts import DoubtAsk, DoubtList, DoubtView
from app.services.gemini import GeminiError, explain_logic, explain_logic_strict


DAILY_LIMIT = 20

CODE_FENCE = re.compile(r"```")
CODE_PATTERNS = [
    re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE),
    re.compile(r"^\s*class\s+\w+", re.MULTILINE),
    re.compile(r"^\s*function\s+\w+\s*\(", re.MULTILINE),
    re.compile(r"^\s*#include\s*<", re.MULTILINE),
    re.compile(r"^\s*public\s+(static\s+)?\w+", re.MULTILINE),
    re.compile(r"^\s*for\s*\([^)]*\)\s*\{", re.MULTILINE),
    re.compile(r"^\s*while\s*\([^)]*\)\s*\{", re.MULTILINE),
    re.compile(r"^\s*if\s*\([^)]*\)\s*\{", re.MULTILINE),
    re.compile(r"^\s*console\.log\(", re.MULTILINE),
    re.compile(r"^\s*print\(", re.MULTILINE),
]

FALLBACK_REPLY = (
    "I can only explain the logic and suggest approaches, not give the final "
    "code or answer. Try restating the question as \"how should I think about "
    "this?\" or \"what are different ways to approach this?\" and I will help "
    "with that."
)


def _student_profile(db: Session, student: User) -> StudentProfile:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == student.id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student academic profile not found.",
        )
    return profile


def _subject_for_student(db: Session, student: User, subject_code: str) -> Subject:
    profile = _student_profile(db, student)
    subject = db.scalar(
        select(Subject).where(
            Subject.code == subject_code,
            Subject.department_id == profile.department_id,
            Subject.year == profile.year,
            Subject.semester == profile.semester,
        )
    )
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")
    return subject


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _used_today(db: Session, student_id: int) -> int:
    since = _today_start_utc()
    return (
        db.scalar(
            select(func.count())
            .select_from(StudentDoubt)
            .where(
                StudentDoubt.student_id == student_id,
                StudentDoubt.created_at >= since,
            )
        )
        or 0
    )


def _looks_like_code(text: str) -> bool:
    if CODE_FENCE.search(text):
        return True
    return any(pattern.search(text) for pattern in CODE_PATTERNS)


def _safe_answer(question: str, subject_label: str) -> str:
    try:
        first = explain_logic(question, subject_label)
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The study helper is unavailable right now. Try again in a moment.",
        ) from exc

    if not _looks_like_code(first):
        return first

    try:
        second = explain_logic_strict(question, subject_label)
    except GeminiError:
        return FALLBACK_REPLY

    if not _looks_like_code(second):
        return second
    return FALLBACK_REPLY


def _doubt_view(doubt: StudentDoubt, subject: Subject) -> DoubtView:
    return DoubtView(
        id=doubt.id,
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        question=doubt.question,
        answer=doubt.answer,
        created_at=doubt.created_at,
    )


def ask_doubt(db: Session, student: User, payload: DoubtAsk) -> DoubtView:
    subject = _subject_for_student(db, student, payload.subject_code)

    used = _used_today(db, student.id)
    if used >= DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached the daily limit of {DAILY_LIMIT} questions. Try again tomorrow.",
        )

    subject_label = f"{subject.code} - {subject.name}"
    answer = _safe_answer(payload.question, subject_label)

    doubt = StudentDoubt(
        student_id=student.id,
        subject_id=subject.id,
        question=payload.question,
        answer=answer,
    )
    db.add(doubt)
    db.add(
        AuditLog(
            actor_id=student.id,
            action="doubt.asked",
            entity_type="student_doubt",
            entity_id=str(subject.id),
        )
    )
    db.commit()
    db.refresh(doubt)

    return _doubt_view(doubt, subject)


def list_doubts(db: Session, student: User) -> DoubtList:
    _student_profile(db, student)

    rows = db.execute(
        select(StudentDoubt, Subject)
        .join(Subject, Subject.id == StudentDoubt.subject_id)
        .where(StudentDoubt.student_id == student.id)
        .order_by(StudentDoubt.created_at.desc(), StudentDoubt.id.desc())
    ).all()

    remaining = max(0, DAILY_LIMIT - _used_today(db, student.id))
    return DoubtList(
        doubts=[_doubt_view(doubt, subject) for doubt, subject in rows],
        remaining_today=remaining,
    )
