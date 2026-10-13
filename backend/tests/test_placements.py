"""Tests for the placements feature."""

from datetime import date, timedelta

from app.core.security import hash_password
from app.models import (
    Department,
    FacultyProfile,
    FacultySubject,
    StudentProfile,
    Subject,
    User,
)

PASSWORD = "PlacementsTest123!"


def placement_records(database):
    with database() as session:
        cs = Department(name="Placement CS", code="PCS")
        other = Department(name="Placement Other", code="POT")
        session.add_all([cs, other])
        session.flush()

        faculty = User(
            email="placement.faculty@example.invalid",
            full_name="Placement Faculty",
            role="faculty",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        student = User(
            email="placement.student@example.invalid",
            full_name="Placement Student",
            role="student",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        outsider = User(
            email="placement.outsider@example.invalid",
            full_name="Outsider Student",
            role="student",
            department_id=other.id,
            password_hash=hash_password(PASSWORD),
        )
        session.add_all([faculty, student, outsider])
        session.flush()

        session.add_all(
            [
                FacultyProfile(user_id=faculty.id, department_id=cs.id),
                StudentProfile(user_id=student.id, department_id=cs.id, year=2, semester=1),
                StudentProfile(user_id=outsider.id, department_id=other.id, year=2, semester=1),
            ]
        )
        session.flush()

        subject = Subject(
            department_id=cs.id,
            code="PCS201",
            name="Placement Subject",
            year=2,
            semester=1,
        )
        other_subject = Subject(
            department_id=other.id,
            code="POT201",
            name="Other Placement Subject",
            year=2,
            semester=1,
        )
        session.add_all([subject, other_subject])
        session.flush()

        session.add(FacultySubject(faculty_id=faculty.id, subject_id=subject.id))
        session.commit()

        return {
            "faculty_email": faculty.email,
            "student_email": student.email,
            "student_id": student.id,
            "outsider_email": outsider.email,
            "outsider_id": outsider.id,
            "subject_id": subject.id,
        }


def bearer(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_faculty_creates_placement_for_own_student(client, database):
    records = placement_records(database)
    headers = bearer(client, records["faculty_email"])

    offer = (date.today() - timedelta(days=10)).isoformat()
    response = client.post(
        "/faculty/placements",
        headers=headers,
        json={
            "student_id": records["student_id"],
            "company": "Acme Corp",
            "role": "Software Engineer",
            "package_lpa": 12.5,
            "offer_date": offer,
            "status": "accepted",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Placement recorded."

    listing = client.get("/faculty/placements", headers=headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["company"] == "Acme Corp"
    assert rows[0]["package_lpa"] == 12.5
    assert rows[0]["student_email"] == records["student_email"]


def test_faculty_cannot_place_outside_student(client, database):
    records = placement_records(database)
    headers = bearer(client, records["faculty_email"])

    response = client.post(
        "/faculty/placements",
        headers=headers,
        json={
            "student_id": records["outsider_id"],
            "company": "Acme Corp",
            "role": "Software Engineer",
            "offer_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 404


def test_student_cannot_access_placements_endpoint(client, database):
    records = placement_records(database)
    headers = bearer(client, records["student_email"])

    assert client.get("/faculty/placements", headers=headers).status_code == 403
    assert (
        client.post(
            "/faculty/placements",
            headers=headers,
            json={
                "student_id": records["student_id"],
                "company": "Acme",
                "role": "Engineer",
                "offer_date": date.today().isoformat(),
            },
        ).status_code
        == 403
    )
