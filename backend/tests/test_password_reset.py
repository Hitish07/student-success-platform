import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.core.security import hash_password
from app.models.models import PasswordResetToken, User

EMAIL = "reset.user@example.invalid"
OLD = "OldPassword123!"
NEW = "BrandNewPass456!"


def make_user(database):
    with database() as db:
        db.add(User(email=EMAIL, full_name="Reset User", role="student", password_hash=hash_password(OLD)))
        db.commit()


def request_token(client, caplog):
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        response = client.post("/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 202
    match = re.search(r"token=([A-Za-z0-9_-]+)", caplog.text)
    assert match, "reset link was not logged"
    return match.group(1)


def login_status(client, password):
    return client.post("/auth/login", json={"email": EMAIL, "password": password}).status_code


def test_unknown_email_gets_same_answer_and_no_link(client, database, caplog):
    make_user(database)
    with caplog.at_level(logging.WARNING):
        known = client.post("/auth/forgot-password", json={"email": EMAIL})
        unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.invalid"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert "nobody@example.invalid" not in caplog.text


def test_reset_changes_password_and_token_is_single_use(client, database, caplog):
    make_user(database)
    token = request_token(client, caplog)
    done = client.post("/auth/reset-password", json={"token": token, "new_password": NEW})
    assert done.status_code == 200
    assert login_status(client, NEW) == 200
    assert login_status(client, OLD) == 401
    again = client.post("/auth/reset-password", json={"token": token, "new_password": "AnotherPass789!"})
    assert again.status_code == 400
    assert login_status(client, NEW) == 200


def test_new_request_invalidates_previous_token(client, database, caplog):
    make_user(database)
    first = request_token(client, caplog)
    second = request_token(client, caplog)
    assert client.post("/auth/reset-password", json={"token": first, "new_password": NEW}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": second, "new_password": NEW}).status_code == 200


def test_expired_or_invalid_token_and_weak_password_rejected(client, database, caplog):
    make_user(database)
    token = request_token(client, caplog)
    bad = client.post("/auth/reset-password", json={"token": "x" * 43, "new_password": NEW})
    assert bad.status_code == 400
    short = client.post("/auth/reset-password", json={"token": token, "new_password": "short"})
    assert short.status_code == 422
    with database() as db:
        db.execute(update(PasswordResetToken).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()
    expired = client.post("/auth/reset-password", json={"token": token, "new_password": NEW})
    assert expired.status_code == 400
    assert login_status(client, OLD) == 200


def test_change_password_requires_correct_current_password(client, database):
    make_user(database)
    login = client.post("/auth/login", json={"email": EMAIL, "password": OLD})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}

    wrong = client.post(
        "/auth/change-password", headers=headers, json={"current_password": "WrongPassword999!", "new_password": NEW}
    )
    assert wrong.status_code == 400
    same = client.post("/auth/change-password", headers=headers, json={"current_password": OLD, "new_password": OLD})
    assert same.status_code == 400
    short = client.post("/auth/change-password", headers=headers, json={"current_password": OLD, "new_password": "short"})
    assert short.status_code == 422
    assert client.post("/auth/change-password", json={"current_password": OLD, "new_password": NEW}).status_code in {401, 403}
    assert login_status(client, OLD) == 200

    done = client.post("/auth/change-password", headers=headers, json={"current_password": OLD, "new_password": NEW})
    assert done.status_code == 200
    assert login_status(client, NEW) == 200
    assert login_status(client, OLD) == 401
