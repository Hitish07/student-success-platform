"""Tests for the faculty Student 360 endpoint."""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.models import (
    Assessment,
    Attendance,
    Course,
    Department,
    FacultyProfile,
    FacultySubject,
    Mark,
    StudentDoubt,
    StudentProfile,
    Subject,
    User,
)

PASSWORD = "Student360Test123!"


def student360_records(database):
    with database() as session:
        cs = Department(name="CS Dept", code="CSE")
        other = Department(name="Other Dept", code="OTH")
        session.add_all([cs, other])
        session.flush()

        faculty = User(
            email="s360.faculty@example.invalid",
            full_name="S360 Faculty",
            role="faculty",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        other_faculty = User(
            email="s360.other.faculty@example.invalid",
            full_name="Other Faculty",
            role="faculty",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        student = User(
            email="s360.student@example.invalid",
            full_name="S360 Student",
            role="student",
            department_id=cs.id,
            password_hash=hash_password(PASSWORD),
        )
        outsider = User(
            email="s360.outsider@example.invalid",
            full_name="Outsider Student",
            role="student",
            department_id=other.id,
            password_hash=hash_password(PASSWORD),
        )
        session.add_all([faculty, other_faculty, student, outsider])
        session.flush()

        session.add_all(
            [
                FacultyProfile(user_id=faculty.id, department_id=cs.id),
                FacultyProfile(user_id=other_faculty.id, department_id=cs.id),
                StudentProfile(user_id=student.id, department_id=cs.id, year=2, semester=1),
                StudentProfile(user_id=outsider.id, department_id=other.id, year=2, semester=1),
            ]
        )
        session.flush()

        subject = Subject(
            department_id=cs.id,
            code="S360201",
            name="Student 360",
            year=2,
            semester=1,
        )
        other_subject = Subject(
            department_id=other.id,
            code="OTH201",
            name="Other Subject",
            year=2,
            semester=1,
        )
        session.add_all([subject, other_subject])
        session.flush()

        session.add(FacultySubject(faculty_id=faculty.id, subject_id=subject.id))
        session.flush()

        course = Course(
            department_id=cs.id,
            faculty_id=faculty.id,
            code="S360201",
            name="Student 360",
            credits=3,
        )
        session.add(course)
        session.flush()

        assessment = Assessment(
            course_id=course.id,
            title="Midterm",
            assessment_type="exam",
            max_score=Decimal("100.00"),
            due_date=date.today(),
        )
        session.add(assessment)
        session.flush()

        session.add_all(
            [
                Mark(
                    student_id=student.id,
                    assessment_id=assessment.id,
                    score=Decimal("80.00"),
                    submitted_at=datetime.now(timezone.utc),
                    is_submitted=True,
                ),
                Attendance(
                    student_id=student.id,
                    course_id=course.id,
                    class_date=date.today(),
                    status="present",
                ),
            ]
        )
        session.commit()

        return {
            "faculty_email": faculty.email,
            "other_faculty_email": other_faculty.email,
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


def test_faculty_can_read_own_student(client, database):
    records = student360_records(database)
    headers = bearer(client, records["faculty_email"])

    response = client.get(
        f"/faculty/students/{records['student_id']}/summary",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["header"]["full_name"] == "S360 Student"
    assert body["header"]["year"] == 2
    assert body["header"]["semester"] == 1
    assert body["metrics"]["attendance_percentage"] == 100.0
    assert body["metrics"]["marks_percentage"] == 80.0


def test_faculty_cannot_read_outside_student(client, database):
    records = student360_records(database)
    headers = bearer(client, records["faculty_email"])

    # The outsider is in another department; faculty must not see them.
    response = client.get(
        f"/faculty/students/{records['outsider_id']}/summary",
        headers=headers,
    )
    assert response.status_code == 404


def test_student_token_cannot_read_student_360(client, database):
    records = student360_records(database)
    headers = bearer(client, records["student_email"])

    response = client.get(
        f"/faculty/students/{records['student_id']}/summary",
        headers=headers,
    )
    assert response.status_code == 403
