"""Tests for the principal dashboard endpoint.

Gemini is mocked so tests do not call the real API.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.security import hash_password
from app.models import (
    Assessment,
    Attendance,
    Course,
    Department,
    Mark,
    StudentProfile,
    User,
)

PASSWORD = "PrincipalTest123!"


def principal_records(database):
    with database() as session:
        cs = Department(name="Computer Science", code="CSE")
        mech = Department(name="Mechanical", code="MEC")
        session.add_all([cs, mech])
        session.flush()

        principal = User(
            email="principal@example.invalid",
            full_name="Test Principal",
            role="principal",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        cs_student = User(
            email="cs.student@example.invalid",
            full_name="CS Student",
            role="student",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        mech_student = User(
            email="mech.student@example.invalid",
            full_name="Mech Student",
            role="student",
            department_id=mech.id,
            password_hash=hash_password(PASSWORD),
        )
        faculty = User(
            email="cs.faculty@example.invalid",
            full_name="CS Faculty",
            role="faculty",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        session.add_all([principal, cs_student, mech_student, faculty])
        session.flush()

        session.add_all(
            [
                StudentProfile(user_id=cs_student.id, department_id=cs.id, year=2, semester=1),
                StudentProfile(user_id=mech_student.id, department_id=mech.id, year=2, semester=1),
            ]
        )
        session.flush()

        cs_course = Course(
            department_id=cs.id,
            faculty_id=faculty.id,
            code="CS201",
            name="Data Structures",
            credits=3,
        )
        mech_course = Course(
            department_id=mech.id,
            faculty_id=faculty.id,
            code="ME201",
            name="Thermodynamics",
            credits=3,
        )
        session.add_all([cs_course, mech_course])
        session.flush()

        cs_assessment = Assessment(
            course_id=cs_course.id,
            title="CS midterm",
            assessment_type="exam",
            max_score=Decimal("100.00"),
            due_date=date.today(),
        )
        mech_assessment = Assessment(
            course_id=mech_course.id,
            title="Mech midterm",
            assessment_type="exam",
            max_score=Decimal("100.00"),
            due_date=date.today(),
        )
        session.add_all([cs_assessment, mech_assessment])
        session.flush()

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                Mark(
                    student_id=cs_student.id,
                    assessment_id=cs_assessment.id,
                    score=Decimal("80.00"),
                    submitted_at=now,
                    is_submitted=True,
                ),
                Mark(
                    student_id=mech_student.id,
                    assessment_id=mech_assessment.id,
                    score=Decimal("60.00"),
                    submitted_at=now,
                    is_submitted=True,
                ),
                Attendance(
                    student_id=cs_student.id,
                    course_id=cs_course.id,
                    class_date=date.today(),
                    status="present",
                ),
                Attendance(
                    student_id=mech_student.id,
                    course_id=mech_course.id,
                    class_date=date.today(),
                    status="absent",
                ),
            ]
        )
        session.commit()


def bearer(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def fake_summary(monkeypatch):
    def fake(stats):
        return "A short institutional briefing generated for the test."

    import app.services.principal_portal as principal_service
    monkeypatch.setattr(principal_service, "summarize_dashboard", fake)


def test_principal_dashboard_shape(client, database, fake_summary):
    principal_records(database)
    headers = bearer(client, "principal@example.invalid")

    response = client.get("/principal/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total_students"] == 2
    assert body["average_marks"] == pytest.approx(70.0, abs=0.5)
    assert body["average_attendance"] == pytest.approx(50.0, abs=0.5)

    inst = body["academic_trend"]["institution"]
    assert len(inst) == 6
    assert sum(point["value"] for point in inst) > 0

    departments = [line["name"] for line in body["academic_trend"]["by_department"]]
    assert "Computer Science" in departments
    assert "Mechanical" in departments

    assert body["placement_readiness"]["overall_average"] == 0.0
    assert body["ai_summary"] == "A short institutional briefing generated for the test."


def test_principal_dashboard_requires_principal_role(client, database, fake_summary):
    principal_records(database)

    student_headers = bearer(client, "cs.student@example.invalid")
    assert client.get("/principal/dashboard", headers=student_headers).status_code == 403

    assert client.get("/principal/dashboard").status_code == 401
