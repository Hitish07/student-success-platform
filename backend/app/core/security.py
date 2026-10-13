from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "student-success-platform"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(
    *,
    user_id: int,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + expires_delta
    token_id = jti or str(uuid4())
    claims = {
        "sub": str(user_id),
        "role": role,
        "typ": token_type,
        "jti": token_id,
        "iss": JWT_ISSUER,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token, token_id, expires_at


def decode_token(token: str, expected_type: str) -> dict[str, object]:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss", "sub", "jti", "typ", "role"]},
    )
    if claims.get("typ") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type.")
    return claims
