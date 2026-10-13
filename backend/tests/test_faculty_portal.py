from datetime import date, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.models import (
    Alert,
    Assessment,
    Attendance,
    AuditLog,
    Course,
    Department,
    Enrollment,
    FacultyFeedback,
    Intervention,
    Mark,
    RiskScore,
    StudentNote,
    User,
)


def faculty_records(database):
    with database() as session:
        department = Department(name="Faculty Portal Department", code="FAC")
        session.add(department)
        session.flush()
        faculty_a = User(
            email="faculty.scope.a@demo.invalid",
            full_name="Faculty Scope A",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password("FacultyPass123!"),
        )
        faculty_b = User(
            email="faculty.scope.b@demo.invalid",
            full_name="Faculty Scope B",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password("FacultyPass123!"),
        )
        student_a = User(
            email="student.scope.a@demo.invalid",
            full_name="Student Scope A",
            role="student",
            department_id=department.id,
            password_hash=hash_password("FacultyPass123!"),
        )
        student_b = User(
            email="student.scope.b@demo.invalid",
            full_name="Student Scope B",
            role="student",
            department_id=department.id,
            password_hash=hash_password("FacultyPass123!"),
        )
        session.add_all([faculty_a, faculty_b, student_a, student_b])
        session.flush()
        course_a = Course(
            department_id=department.id,
            faculty_id=faculty_a.id,
            code="FAC101",
            name="Faculty A Course",
            credits=3,
        )
        course_b = Course(
            department_id=department.id,
            faculty_id=faculty_b.id,
            code="FAC202",
            name="Faculty B Course",
            credits=3,
        )
        session.add_all([course_a, course_b])
        session.flush()
        session.add_all(
            [
                Enrollment(student_id=student_a.id, course_id=course_a.id, semester="Fall 2026"),
                Enrollment(student_id=student_b.id, course_id=course_b.id, semester="Fall 2026"),
            ]
        )
        assessment_a = Assessment(
            course_id=course_a.id,
            title="A Quiz",
            assessment_type="quiz",
            max_score=Decimal("20"),
            due_date=date.today() + timedelta(days=7),
        )
        assessment_b = Assessment(
            course_id=course_b.id,
            title="B Quiz",
            assessment_type="quiz",
            max_score=Decimal("20"),
            due_date=date.today() + timedelta(days=7),
        )
        session.add_all([assessment_a, assessment_b])
        session.flush()
        attendance_a = Attendance(
            student_id=student_a.id,
            course_id=course_a.id,
            class_date=date.today() - timedelta(days=3),
            status="present",
        )
        attendance_b = Attendance(
            student_id=student_b.id,
            course_id=course_b.id,
            class_date=date.today() - timedelta(days=3),
            status="absent",
        )
        mark_a = Mark(
            student_id=student_a.id,
            assessment_id=assessment_a.id,
            score=Decimal("15"),
        )
        mark_b = Mark(
            student_id=student_b.id,
            assessment_id=assessment_b.id,
            score=Decimal("5"),
        )
        note_b = StudentNote(
            student_id=student_b.id,
            author_id=faculty_b.id,
            content="Private B note.",
        )
        intervention_b = Intervention(
            student_id=student_b.id,
            assigned_by=faculty_b.id,
            intervention_type="mentoring",
            description="Private B intervention.",
            start_date=date.today() - timedelta(days=1),
        )
        session.add_all(
            [
                attendance_a,
                attendance_b,
                mark_a,
                mark_b,
                note_b,
                intervention_b,
                RiskScore(
                    student_id=student_a.id,
                    score=Decimal("0.8000"),
                    risk_level="high",
                    contributing_factors={"attendance_rate": 0.4},
                ),
                RiskScore(
                    student_id=student_b.id,
                    score=Decimal("0.9000"),
                    risk_level="high",
                    contributing_factors={"attendance_rate": 0.2},
                ),
                Alert(
                    student_id=student_a.id,
                    alert_type="risk_threshold",
                    severity="high",
                    status="open",
                ),
                Alert(
                    student_id=student_b.id,
                    alert_type="risk_threshold",
                    severity="critical",
                    status="open",
                ),
                FacultyFeedback(
                    student_id=student_a.id,
                    faculty_id=faculty_a.id,
                    course_id=course_a.id,
                    rating=5,
                    comments="A feedback.",
                ),
                FacultyFeedback(
                    student_id=student_b.id,
                    faculty_id=faculty_b.id,
                    course_id=course_b.id,
                    rating=1,
                    comments="B private feedback.",
                ),
            ]
        )
        session.commit()
        return {
            "faculty_a": faculty_a.id,
            "faculty_b": faculty_b.id,
            "student_a": student_a.id,
            "student_b": student_b.id,
            "course_a": course_a.id,
            "course_b": course_b.id,
            "assessment_a": assessment_a.id,
            "assessment_b": assessment_b.id,
            "attendance_a": attendance_a.id,
            "attendance_b": attendance_b.id,
            "mark_a": mark_a.id,
            "mark_b": mark_b.id,
            "note_b": note_b.id,
            "intervention_b": intervention_b.id,
        }


def faculty_headers(client, email="faculty.scope.a@demo.invalid"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "FacultyPass123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_faculty_a_cannot_read_or_modify_faculty_b_records(client, database):
    records = faculty_records(database)
    headers = faculty_headers(client)

    dashboard = client.get("/faculty/dashboard", headers=headers)
    alerts = client.get("/faculty/alerts", headers=headers)
    at_risk = client.get("/faculty/at-risk", headers=headers)
    feedback = client.get("/faculty/feedback", headers=headers)
    attendance = client.get("/faculty/attendance", headers=headers)
    private_course_students = client.get(
        f"/faculty/courses/{records['course_b']}/students", headers=headers
    )
    private_assessments = client.get(
        f"/faculty/courses/{records['course_b']}/assessments", headers=headers
    )
    private_marks = client.get(
        f"/faculty/courses/{records['course_b']}/marks", headers=headers
    )
    private_notes = client.get(
        f"/faculty/students/{records['student_b']}/notes", headers=headers
    )
    private_interventions = client.get(
        f"/faculty/students/{records['student_b']}/interventions", headers=headers
    )
    assert dashboard.status_code == 200
    assert [row["code"] for row in dashboard.json()["courses"]] == ["FAC101"]
    assert "Student Scope B" not in str(alerts.json())
    assert "Student Scope B" not in str(at_risk.json())
    assert "B private" not in str(feedback.json())
    assert "Student Scope B" not in str(attendance.json())
    assert all(
        response.status_code == 404
        for response in (
            private_course_students,
            private_assessments,
            private_marks,
            private_notes,
            private_interventions,
        )
    )

    foreign_attendance = client.post(
        "/faculty/attendance",
        headers=headers,
        json={
            "student_id": records["student_b"],
            "course_id": records["course_b"],
            "class_date": str(date.today() - timedelta(days=1)),
            "status": "present",
        },
    )
    foreign_mark = client.post(
        "/faculty/marks",
        headers=headers,
        json={
            "student_id": records["student_b"],
            "assessment_id": records["assessment_b"],
            "score": 10,
        },
    )
    foreign_note = client.post(
        "/faculty/notes",
        headers=headers,
        json={"student_id": records["student_b"], "content": "Forged note."},
    )
    foreign_intervention = client.post(
        "/faculty/interventions",
        headers=headers,
        json={
            "student_id": records["student_b"],
            "intervention_type": "mentoring",
            "description": "Forged intervention.",
            "start_date": str(date.today()),
        },
    )
    updates = (
        client.put(
            f"/faculty/attendance/{records['attendance_b']}",
            headers=headers,
            json={"class_date": str(date.today()), "status": "present"},
        ),
        client.put(
            f"/faculty/marks/{records['mark_b']}",
            headers=headers,
            json={"score": 10, "is_submitted": True},
        ),
        client.put(
            f"/faculty/notes/{records['note_b']}",
            headers=headers,
            json={"content": "Forged update."},
        ),
    )
    assert all(
        response.status_code == 404
        for response in (
            foreign_attendance,
            foreign_mark,
            foreign_note,
            foreign_intervention,
            *updates,
        )
    )

    with database() as session:
        assert session.get(Attendance, records["attendance_b"]).status == "absent"
        assert session.get(Mark, records["mark_b"]).score == Decimal("5.00")
        assert session.get(StudentNote, records["note_b"]).content == "Private B note."
        assert session.get(Intervention, records["intervention_b"]).description == "Private B intervention."


def test_faculty_validates_records_and_audits_mutations(client, database):
    records = faculty_records(database)
    headers = faculty_headers(client)
    past = str(date.today() - timedelta(days=1))
    future = str(date.today() + timedelta(days=1))

    future_attendance = client.post(
        "/faculty/attendance",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "course_id": records["course_a"],
            "class_date": future,
            "status": "present",
        },
    )
    duplicate_attendance = client.post(
        "/faculty/attendance",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "course_id": records["course_a"],
            "class_date": str(date.today() - timedelta(days=3)),
            "status": "absent",
        },
    )
    assert future_attendance.status_code == 422
    assert duplicate_attendance.status_code == 409

    new_attendance = client.post(
        "/faculty/attendance",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "course_id": records["course_a"],
            "class_date": past,
            "status": "late",
        },
    )
    assert new_attendance.status_code == 201
    attendance_id = new_attendance.json()["id"]
    attendance_update = client.put(
        f"/faculty/attendance/{attendance_id}",
        headers=headers,
        json={"class_date": past, "status": "present"},
    )
    over_mark = client.post(
        "/faculty/marks",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "assessment_id": records["assessment_a"],
            "score": 21,
        },
    )
    new_mark = client.post(
        "/faculty/marks",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "assessment_id": records["assessment_a"],
            "score": 18,
        },
    )
    created_assessment = client.post(
        f"/faculty/courses/{records['course_a']}/assessments",
        headers=headers,
        json={
            "title": "New assignment",
            "assessment_type": "assignment",
            "max_score": 25,
            "due_date": future,
        },
    )
    assert attendance_update.status_code == 200
    assert over_mark.status_code == 422
    assert new_mark.status_code == 409
    assert created_assessment.status_code == 201
    created_mark = client.post(
        "/faculty/marks",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "assessment_id": created_assessment.json()["id"],
            "score": 21,
        },
    )
    assert created_mark.status_code == 201
    mark_update = client.put(
        f"/faculty/marks/{records['mark_a']}",
        headers=headers,
        json={"score": 19, "is_submitted": True},
    )
    assert mark_update.status_code == 200

    note = client.post(
        "/faculty/notes",
        headers=headers,
        json={"student_id": records["student_a"], "content": "Check in next week."},
    )
    assert note.status_code == 201
    note_update = client.put(
        f"/faculty/notes/{note.json()['id']}",
        headers=headers,
        json={"content": "Follow-up meeting scheduled."},
    )
    intervention = client.post(
        "/faculty/interventions",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "intervention_type": "mentoring",
            "description": "Weekly mentoring.",
            "start_date": past,
        },
    )
    future_intervention = client.post(
        "/faculty/interventions",
        headers=headers,
        json={
            "student_id": records["student_a"],
            "intervention_type": "mentoring",
            "description": "Future mentoring.",
            "start_date": future,
        },
    )
    assert note_update.status_code == 200
    assert intervention.status_code == 201
    assert future_intervention.status_code == 422

    with database() as session:
        audit_rows = list(session.query(AuditLog).filter_by(actor_id=records["faculty_a"]).all())
        actions = {row.action for row in audit_rows}
        assert {
            "attendance.created",
            "attendance.updated",
            "mark.created",
            "mark.updated",
            "student_note.created",
            "student_note.updated",
            "intervention.created",
        } <= actions
        assert all(row.entity_id is not None for row in audit_rows)
        assert session.get(Attendance, attendance_id).status == "present"
        assert session.get(Mark, records["mark_a"]).score == Decimal("19.00")
