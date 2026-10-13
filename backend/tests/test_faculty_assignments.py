from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import (
    Assignment,
    AssignmentSubmission,
    AuditLog,
    Department,
    FacultyProfile,
    FacultySubject,
    StudentProfile,
    Subject,
    User,
)

PASSWORD = "FacultyTest123!"


def assignment_records(database):
    with database() as session:
        department = Department(name="Assignments Department", code="ASG")
        other_department = Department(name="Other Assignments Department", code="OAS")
        session.add_all([department, other_department])
        session.flush()
        faculty = User(
            email="assignment.faculty@example.invalid",
            full_name="Assignment Faculty",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password(PASSWORD),
        )
        other_faculty = User(
            email="other.assignment.faculty@example.invalid",
            full_name="Other Faculty",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password(PASSWORD),
        )
        student = User(
            email="assignment.student@example.invalid",
            full_name="Matching Student",
            role="student",
            department_id=department.id,
            password_hash=hash_password(PASSWORD),
        )
        wrong_year = User(
            email="wrong.year@example.invalid",
            full_name="Wrong Year Student",
            role="student",
            department_id=department.id,
            password_hash=hash_password(PASSWORD),
        )
        other_department_student = User(
            email="other.department@example.invalid",
            full_name="Other Department Student",
            role="student",
            department_id=other_department.id,
            password_hash=hash_password(PASSWORD),
        )
        session.add_all([faculty, other_faculty, student, wrong_year, other_department_student])
        session.flush()
        session.add_all(
            [
                FacultyProfile(user_id=faculty.id, department_id=department.id),
                FacultyProfile(user_id=other_faculty.id, department_id=department.id),
                StudentProfile(user_id=student.id, department_id=department.id, year=2, semester=1),
                StudentProfile(user_id=wrong_year.id, department_id=department.id, year=3, semester=1),
                StudentProfile(
                    user_id=other_department_student.id,
                    department_id=other_department.id,
                    year=2,
                    semester=1,
                ),
            ]
        )
        subject = Subject(
            department_id=department.id,
            code="ASG201",
            name="Assignment Systems",
            year=2,
            semester=1,
        )
        other_subject = Subject(
            department_id=department.id,
            code="ASG301",
            name="Advanced Assignment Systems",
            year=3,
            semester=1,
        )
        private_subject = Subject(
            department_id=other_department.id,
            code="OAS201",
            name="Private Assignment Systems",
            year=2,
            semester=1,
        )
        session.add_all([subject, other_subject, private_subject])
        session.flush()
        session.add_all(
            [
                FacultySubject(faculty_id=faculty.id, subject_id=subject.id),
                FacultySubject(faculty_id=other_faculty.id, subject_id=other_subject.id),
            ]
        )
        assignment = Assignment(
            subject_id=subject.id,
            faculty_id=faculty.id,
            title="Systems assignment",
            description="Work through the exercises.",
            due_date=date.today() + timedelta(days=7),
            max_marks=Decimal("50.00"),
        )
        other_assignment = Assignment(
            subject_id=private_subject.id,
            faculty_id=other_faculty.id,
            title="Private assignment",
            due_date=date.today() + timedelta(days=7),
            max_marks=Decimal("40.00"),
        )
        wrong_year_assignment = Assignment(
            subject_id=other_subject.id,
            faculty_id=other_faculty.id,
            title="Wrong year assignment",
            due_date=date.today() + timedelta(days=7),
            max_marks=Decimal("30.00"),
        )
        session.add_all([assignment, other_assignment, wrong_year_assignment])
        session.commit()
        return {
            "department_id": department.id,
            "other_department_id": other_department.id,
            "faculty_id": faculty.id,
            "other_faculty_id": other_faculty.id,
            "student_id": student.id,
            "subject_id": subject.id,
            "other_subject_id": other_subject.id,
            "private_subject_id": private_subject.id,
            "assignment_id": assignment.id,
            "other_assignment_id": other_assignment.id,
        }


def bearer(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_faculty_registration_creates_profile_subjects_and_omits_hash(client, database):
    with database() as session:
        department = Department(name="New Faculty Department", code="NFD")
        other_department = Department(name="New Faculty Other", code="NFO")
        session.add_all([department, other_department])
        session.flush()
        subject = Subject(
            department_id=department.id,
            code="NFD101",
            name="Faculty Foundations",
            year=1,
            semester=1,
        )
        outside_subject = Subject(
            department_id=other_department.id,
            code="NFO101",
            name="Other Foundations",
            year=1,
            semester=1,
        )
        session.add_all([subject, outside_subject])
        session.commit()
        department_id = department.id
        subject_id = subject.id
        outside_subject_id = outside_subject.id

    payload = {
        "name": "New Faculty",
        "email": "new.faculty@example.invalid",
        "password": PASSWORD,
        "department_id": department_id,
        "subject_ids": [subject_id],
    }
    registered = client.post("/auth/register/faculty", json=payload)
    assert registered.status_code == 201
    assert registered.json()["user"]["role"] == "faculty"
    assert "password_hash" not in registered.text
    with database() as session:
        new_user = session.scalar(select_user_by_email("new.faculty@example.invalid"))
        assert new_user is not None
        profile = session.query(FacultyProfile).filter_by(user_id=new_user.id).one()
        assert profile.department_id == department_id
        assert session.query(FacultySubject).filter_by(faculty_id=new_user.id).count() == 1

    invalid = client.post(
        "/auth/register/faculty",
        json={**payload, "email": "invalid.faculty@example.invalid", "subject_ids": [outside_subject_id]},
    )
    assert invalid.status_code == 422
    assert client.post("/auth/register/faculty", json=payload).status_code == 409
    assert client.post(
        "/auth/register/faculty",
        json={**payload, "email": "role.faculty@example.invalid", "role": "principal"},
    ).status_code == 422


def select_user_by_email(email):
    return select(User).where(User.email == email)


def test_faculty_can_create_assignments_only_for_taught_subjects_and_audits(client, database):
    records = assignment_records(database)
    faculty_headers = bearer(client, "assignment.faculty@example.invalid")
    create = client.post(
        "/faculty/assignments",
        headers=faculty_headers,
        json={
            "subject_id": records["subject_id"],
            "title": "New assignment",
            "description": "Complete the exercise set.",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "max_marks": 25,
        },
    )
    assert create.status_code == 201
    assert create.json()["subject_code"] == "ASG201"
    assert client.post(
        "/faculty/assignments",
        headers=faculty_headers,
        json={
            "subject_id": records["other_subject_id"],
            "title": "Not mine",
            "due_date": date.today().isoformat(),
            "max_marks": 10,
        },
    ).status_code == 404
    assert client.post(
        "/faculty/assignments",
        headers=faculty_headers,
        json={
            "subject_id": records["subject_id"],
            "title": "Invalid marks",
            "due_date": date.today().isoformat(),
            "max_marks": 0,
        },
    ).status_code == 422
    with database() as session:
        audit_rows = session.query(AuditLog).filter_by(
            actor_id=records["faculty_id"],
            action="assignment.created",
        ).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].entity_id == str(create.json()["id"])
        listed = client.get("/faculty/assignments", headers=faculty_headers)
        assert listed.status_code == 200
        assert [item["title"] for item in listed.json()] == [
            "New assignment",
            "Systems assignment",
        ]


def test_faculty_roster_is_scoped_to_taught_subject_and_matching_academics(client, database):
    records = assignment_records(database)
    faculty_headers = bearer(client, "assignment.faculty@example.invalid")
    response = client.get(
        f"/faculty/subjects/{records['subject_id']}/students",
        headers=faculty_headers,
    )
    assert response.status_code == 200
    assert [row["email"] for row in response.json()] == ["assignment.student@example.invalid"]

    other_faculty_headers = bearer(client, "other.assignment.faculty@example.invalid")
    denied = client.get(
        f"/faculty/subjects/{records['subject_id']}/students",
        headers=other_faculty_headers,
    )
    assert denied.status_code == 404


def test_student_sees_and_submits_only_current_academic_assignments(client, database):
    records = assignment_records(database)
    student_headers = bearer(client, "assignment.student@example.invalid")
    response = client.get("/student/assignments", headers=student_headers)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [records["assignment_id"]]
    assert response.json()[0]["status"] in {"open", "overdue"}

    forbidden = client.post(
        f"/student/assignments/{records['other_assignment_id']}/submit",
        headers=student_headers,
        json={"answer_text": "My answer"},
    )
    assert forbidden.status_code == 404
    submitted = client.post(
        f"/student/assignments/{records['assignment_id']}/submit",
        headers=student_headers,
        json={"answer_text": "My answer"},
    )
    assert submitted.status_code == 201
    assert client.post(
        f"/student/assignments/{records['assignment_id']}/submit",
        headers=student_headers,
        json={"answer_text": "Second attempt"},
    ).status_code == 409
    refreshed = client.get("/student/assignments", headers=student_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()[0]["status"] == "submitted"
    assert client.get("/student/assignments").status_code == 401
    assert client.get("/faculty/my-subjects", headers=student_headers).status_code == 403
    assert client.get("/portals/principal", headers=student_headers).status_code == 403


def test_assignment_submission_unique_constraint(database):
    records = assignment_records(database)
    with database() as session:
        session.add(
            AssignmentSubmission(
                assignment_id=records["assignment_id"],
                student_id=records["student_id"],
            )
        )
        session.commit()
        session.add(
            AssignmentSubmission(
                assignment_id=records["assignment_id"],
                student_id=records["student_id"],
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_submission_saves_and_returns_answer_text(client, database):
    records = assignment_records(database)
    headers = bearer(client, "assignment.student@example.invalid")
    url = f"/student/assignments/{records['assignment_id']}/submit"

    response = client.post(url, headers=headers, json={"answer_text": "  My written answer  "})
    assert response.status_code == 201

    listed = client.get("/student/assignments", headers=headers).json()
    row = next(item for item in listed if item["id"] == records["assignment_id"])
    assert row["status"] == "submitted"
    assert row["answer_text"] == "My written answer"


def test_submission_rejects_empty_or_whitespace_answer(client, database):
    records = assignment_records(database)
    headers = bearer(client, "assignment.student@example.invalid")
    url = f"/student/assignments/{records['assignment_id']}/submit"

    assert client.post(url, headers=headers, json={"answer_text": ""}).status_code == 422
    assert client.post(url, headers=headers, json={"answer_text": "   \n  "}).status_code == 422
    assert client.post(url, headers=headers, json={}).status_code == 422

    listed = client.get("/student/assignments", headers=headers).json()
    row = next(item for item in listed if item["id"] == records["assignment_id"])
    assert row["status"] != "submitted"
    assert row["answer_text"] is None


def test_submission_rejects_extra_fields_and_oversized_answer(client, database):
    records = assignment_records(database)
    headers = bearer(client, "assignment.student@example.invalid")
    url = f"/student/assignments/{records['assignment_id']}/submit"

    extra = client.post(url, headers=headers, json={"answer_text": "ok", "marks": 100})
    assert extra.status_code == 422

    too_long = client.post(url, headers=headers, json={"answer_text": "x" * 10001})
    assert too_long.status_code == 422


def _grading_setup(client, database):
    from app.models.models import Assignment, User

    records = assignment_records(database)
    student_headers = bearer(client, "assignment.student@example.invalid")
    submitted = client.post(
        f"/student/assignments/{records['assignment_id']}/submit",
        headers=student_headers,
        json={"answer_text": "Student answer"},
    )
    assert submitted.status_code == 201
    with database() as db:
        assignment = db.get(Assignment, records["assignment_id"])
        owner = db.get(User, assignment.faculty_id)
        owner_email = owner.email
        db.add(
            User(
                email="other.faculty@example.invalid",
                full_name="Other Faculty",
                role="faculty",
                password_hash=owner.password_hash,
            )
        )
        db.commit()
    faculty_headers = bearer(client, owner_email)
    other_headers = bearer(client, "other.faculty@example.invalid")
    listing = client.get(
        f"/faculty/assignments/{records['assignment_id']}/submissions", headers=faculty_headers
    )
    assert listing.status_code == 200
    return records, student_headers, faculty_headers, other_headers, listing.json()


def test_faculty_lists_submissions_only_for_own_assignment(client, database):
    records, student_headers, faculty_headers, other_headers, rows = _grading_setup(client, database)
    assert len(rows) == 1
    assert rows[0]["answer_text"] == "Student answer"
    assert rows[0]["student_email"] == "assignment.student@example.invalid"
    assert rows[0]["marks"] is None
    url = f"/faculty/assignments/{records['assignment_id']}/submissions"
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.get(url, headers=student_headers).status_code in {401, 403}
    assert client.get("/faculty/assignments/999999/submissions", headers=faculty_headers).status_code == 404


def test_faculty_grades_submission_and_student_sees_result(client, database):
    records, student_headers, faculty_headers, other_headers, rows = _grading_setup(client, database)
    sid = rows[0]["id"]
    grade_url = f"/faculty/submissions/{sid}/grade"

    graded = client.put(grade_url, headers=faculty_headers, json={"marks": 7.5, "feedback": "  Good work  "})
    assert graded.status_code == 200
    assert float(graded.json()["marks"]) == 7.5
    assert graded.json()["feedback"] == "Good work"

    mine = client.get("/student/assignments", headers=student_headers).json()
    row = next(item for item in mine if item["id"] == records["assignment_id"])
    assert float(row["marks"]) == 7.5
    assert row["feedback"] == "Good work"

    regraded = client.put(grade_url, headers=faculty_headers, json={"marks": 8, "feedback": None})
    assert regraded.status_code == 200
    assert float(regraded.json()["marks"]) == 8
    assert regraded.json()["feedback"] is None


def test_grading_rejects_invalid_marks_and_other_faculty(client, database):
    records, student_headers, faculty_headers, other_headers, rows = _grading_setup(client, database)
    sid = rows[0]["id"]
    grade_url = f"/faculty/submissions/{sid}/grade"
    over = float(rows[0]["max_marks"]) + 1

    assert client.put(grade_url, headers=faculty_headers, json={"marks": over}).status_code == 422
    assert client.put(grade_url, headers=faculty_headers, json={"marks": -1}).status_code == 422
    assert client.put(grade_url, headers=faculty_headers, json={"marks": 1, "extra": 1}).status_code == 422
    assert client.put(grade_url, headers=faculty_headers, json={}).status_code == 422
    assert client.put(grade_url, headers=other_headers, json={"marks": 1}).status_code == 404
    assert client.put(grade_url, headers=student_headers, json={"marks": 1}).status_code in {401, 403}
    assert client.put("/faculty/submissions/999999/grade", headers=faculty_headers, json={"marks": 1}).status_code == 404

    row = client.get(f"/faculty/assignments/{records['assignment_id']}/submissions", headers=faculty_headers).json()[0]
    assert row["marks"] is None
