"""Tests for the student doubts agent.

Gemini itself is mocked so tests do not burn API quota or depend on
network availability. The mock returns a plain-English reply with no code,
which is what the service expects for the happy path.
"""

import pytest

from app.core.security import hash_password
from app.models import (
    Department,
    StudentProfile,
    Subject,
    User,
)

PASSWORD = "DoubtsTest123!"


def doubt_records(database):
    with database() as session:
        department = Department(name="Doubts Department", code="DBT")
        session.add(department)
        session.flush()

        student = User(
            email="doubts.student@example.invalid",
            full_name="Doubts Student",
            role="student",
            department_id=department.id,
            password_hash=hash_password(PASSWORD),
        )
        session.add(student)
        session.flush()
        session.add(
            StudentProfile(
                user_id=student.id,
                department_id=department.id,
                year=2,
                semester=1,
            )
        )
        session.flush()

        subject = Subject(
            department_id=department.id,
            code="DBT201",
            name="Doubts in Practice",
            year=2,
            semester=1,
        )
        other_subject = Subject(
            department_id=department.id,
            code="DBT301",
            name="Advanced Doubts",
            year=3,
            semester=1,
        )
        session.add_all([subject, other_subject])
        session.commit()

        return {
            "student_id": student.id,
            "subject_code": subject.code,
            "other_subject_code": other_subject.code,
        }


def bearer(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def fake_gemini(monkeypatch):
    calls = {"count": 0}

    def fake_explain(question, subject_label=""):
        calls["count"] += 1
        return (
            "Here is the logic. First think about the base case. "
            "Then consider two approaches: iterative and recursive."
        )

    def fake_strict(question, subject_label=""):
        calls["count"] += 1
        return "Plain-English only: think about the base case, then about each step."

    import app.services.doubts as doubts_service
    monkeypatch.setattr(doubts_service, "explain_logic", fake_explain)
    monkeypatch.setattr(doubts_service, "explain_logic_strict", fake_strict)
    return calls


def test_student_can_ask_and_list_doubts(client, database, fake_gemini):
    records = doubt_records(database)
    headers = bearer(client, "doubts.student@example.invalid")

    ask = client.post(
        "/student/doubts",
        headers=headers,
        json={
            "subject_code": records["subject_code"],
            "question": "How do I think about recursion?",
        },
    )
    assert ask.status_code == 201
    body = ask.json()
    assert body["subject_code"] == records["subject_code"]
    assert body["question"] == "How do I think about recursion?"
    assert "logic" in body["answer"].lower() or "approach" in body["answer"].lower()
    assert fake_gemini["count"] == 1

    listing = client.get("/student/doubts", headers=headers)
    assert listing.status_code == 200
    payload = listing.json()
    assert len(payload["doubts"]) == 1
    assert payload["doubts"][0]["id"] == body["id"]
    assert payload["remaining_today"] == 19


def test_doubt_subject_must_be_in_student_scope(client, database, fake_gemini):
    records = doubt_records(database)
    headers = bearer(client, "doubts.student@example.invalid")

    wrong = client.post(
        "/student/doubts",
        headers=headers,
        json={
            "subject_code": records["other_subject_code"],
            "question": "How do I think about this?",
        },
    )
    assert wrong.status_code == 404
    assert fake_gemini["count"] == 0

    listing = client.get("/student/doubts", headers=headers)
    assert listing.json()["doubts"] == []


def test_doubt_daily_limit(client, database, fake_gemini):
    records = doubt_records(database)
    headers = bearer(client, "doubts.student@example.invalid")

    for index in range(20):
        ok = client.post(
            "/student/doubts",
            headers=headers,
            json={
                "subject_code": records["subject_code"],
                "question": f"Question number {index} about something.",
            },
        )
        assert ok.status_code == 201, f"question {index} failed: {ok.text}"

    blocked = client.post(
        "/student/doubts",
        headers=headers,
        json={
            "subject_code": records["subject_code"],
            "question": "One too many questions.",
        },
    )
    assert blocked.status_code == 429
    assert "daily limit" in blocked.json()["detail"].lower()


def test_faculty_doubts_summary_groups_by_subject(client, database, fake_gemini):
    records = doubt_records(database)
    student_headers = bearer(client, "doubts.student@example.invalid")

    for index in range(3):
        ok = client.post(
            "/student/doubts",
            headers=student_headers,
            json={
                "subject_code": records["subject_code"],
                "question": f"Question {index} about primary subject.",
            },
        )
        assert ok.status_code == 201

    from app.models import FacultyProfile, FacultySubject, User
    with database() as session:
        faculty = User(
            email="doubts.faculty@example.invalid",
            full_name="Doubts Faculty",
            role="faculty",
            department_id=1,
            password_hash=hash_password(PASSWORD),
        )
        session.add(faculty)
        session.flush()
        session.add(FacultyProfile(user_id=faculty.id, department_id=1))
        subject = session.query(Subject).filter(Subject.code == records["subject_code"]).one()
        session.add(FacultySubject(faculty_id=faculty.id, subject_id=subject.id))
        session.commit()

    faculty_headers = bearer(client, "doubts.faculty@example.invalid")
    response = client.get("/faculty/doubts", headers=faculty_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_doubts"] == 3
    assert len(payload["topics"]) == 1
    topic = payload["topics"][0]
    assert topic["subject_code"] == records["subject_code"]
    assert topic["total"] == 3
    assert len(topic["recent"]) == 3
    body_text = response.text
    assert "doubts.student@example.invalid" not in body_text
    assert "Doubts Student" not in body_text


def test_faculty_doubts_summary_empty_for_unrelated_faculty(client, database, fake_gemini):
    records = doubt_records(database)
    student_headers = bearer(client, "doubts.student@example.invalid")

    ok = client.post(
        "/student/doubts",
        headers=student_headers,
        json={
            "subject_code": records["subject_code"],
            "question": "A single question about the subject.",
        },
    )
    assert ok.status_code == 201

    from app.models import FacultyProfile, User
    with database() as session:
        faculty = User(
            email="unrelated.faculty@example.invalid",
            full_name="Unrelated Faculty",
            role="faculty",
            department_id=1,
            password_hash=hash_password(PASSWORD),
        )
        session.add(faculty)
        session.flush()
        session.add(FacultyProfile(user_id=faculty.id, department_id=1))
        session.commit()

    faculty_headers = bearer(client, "unrelated.faculty@example.invalid")
    response = client.get("/faculty/doubts", headers=faculty_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_doubts"] == 0
    assert payload["topics"] == []
