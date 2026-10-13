import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.models import PasswordResetToken, User

logger = logging.getLogger("uvicorn.error")
TOKEN_LIFETIME = timedelta(minutes=30)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_password_reset(db: Session, email: str) -> None:
    user = db.scalar(
        select(User).where(func.lower(User.email) == email.strip().lower(), User.is_active.is_(True))
    )
    if user is None:
        return
    now = datetime.now(timezone.utc)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(user_id=user.id, token_hash=_digest(token), expires_at=now + TOKEN_LIFETIME)
    )
    db.commit()
    # DEMO DELIVERY: prints the link in the backend terminal. Replace with real email before production.
    link = f"{settings.frontend_origins[0]}/reset-password?token={token}"
    logger.warning("PASSWORD RESET LINK for %s: %s", user.email, link)


def reset_password(db: Session, token: str, new_password: str) -> bool:
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _digest(token)))
    now = datetime.now(timezone.utc)
    if record is None or record.used_at is not None:
        return False
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        return False
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        return False
    user.password_hash = hash_password(new_password)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    db.commit()
    return True
