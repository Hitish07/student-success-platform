from datetime import date
from decimal import Decimal

from app.models import (
    Assessment,
    Attendance,
    Course,
    Department,
    Enrollment,
    FacultyFeedback,
    Mark,
    RiskScore,
    StudentFeedback,
    User,
)
from app.core.security import hash_password


def student_portal_records(database):
    with database() as session:
        department = Department(name="Student Portal Department", code="PORTAL")
        session.add(department)
        session.flush()

        faculty_a = User(
            email="faculty.a@demo.invalid",
            full_name="Faculty A",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password("StudentPass123!"),
        )
        faculty_b = User(
            email="faculty.b@demo.invalid",
            full_name="Faculty B",
            role="faculty",
            department_id=department.id,
            password_hash=hash_password("OtherPass123!"),
        )
        student_a = User(
            email="student.a@demo.invalid",
            full_name="Student A",
            role="student",
            department_id=department.id,
            password_hash=hash_password("StudentPass123!"),
        )
        student_b = User(
            email="student.b@demo.invalid",
            full_name="Student B",
            role="student",
            department_id=department.id,
            password_hash=hash_password("StudentPass123!"),
        )
        session.add_all([faculty_a, faculty_b, student_a, student_b])
        session.flush()

        course_a = Course(
            department_id=department.id,
            faculty_id=faculty_a.id,
            code="PORTAL101",
            name="Student A Course",
            credits=3,
        )
        course_b = Course(
            department_id=department.id,
            faculty_id=faculty_b.id,
            code="PRIVATE202",
            name="Student B Private Course",
            credits=3,
        )
        session.add_all([course_a, course_b])
        session.flush()
        session.add_all(
            [
                Enrollment(
                    student_id=student_a.id,
                    course_id=course_a.id,
                    semester="Fall 2026",
                ),
                Enrollment(
                    student_id=student_b.id,
                    course_id=course_b.id,
                    semester="Fall 2026",
                ),
            ]
        )

        assessment_a = Assessment(
            course_id=course_a.id,
            title="A assessment",
            assessment_type="exam",
            max_score=Decimal("100"),
            due_date=date(2026, 10, 15),
        )
        assessment_b = Assessment(
            course_id=course_b.id,
            title="B private assessment",
            assessment_type="exam",
            max_score=Decimal("100"),
            due_date=date(2026, 10, 15),
        )
        session.add_all([assessment_a, assessment_b])
        session.flush()
        session.add_all(
            [
                Mark(
                    student_id=student_a.id,
                    assessment_id=assessment_a.id,
                    score=Decimal("80"),
                    is_submitted=True,
                ),
                Mark(
                    student_id=student_b.id,
                    assessment_id=assessment_b.id,
                    score=Decimal("20"),
                    is_submitted=True,
                ),
                Attendance(
                    student_id=student_a.id,
                    course_id=course_a.id,
                    class_date=date(2026, 9, 1),
                    status="present",
                ),
                Attendance(
                    student_id=student_a.id,
                    course_id=course_a.id,
                    class_date=date(2026, 9, 8),
                    status="absent",
                ),
                RiskScore(
                    student_id=student_a.id,
                    score=Decimal("0.2000"),
                    risk_level="medium",
                    contributing_factors={
                        "attendance_rate": 0.5,
                        "average_mark_rate": 0.8,
                        "missed_submissions": 1,
                    },
                ),
                RiskScore(
                    student_id=student_b.id,
                    score=Decimal("0.9000"),
                    risk_level="high",
                    contributing_factors={"attendance_rate": 0.1},
                ),
                StudentFeedback(
                    student_id=student_a.id,
                    faculty_id=faculty_a.id,
                    course_id=course_a.id,
                    message="A feedback only.",
                ),
                StudentFeedback(
                    student_id=student_b.id,
                    faculty_id=faculty_b.id,
                    course_id=course_b.id,
                    message="B private faculty feedback.",
                ),
                FacultyFeedback(
                    student_id=student_a.id,
                    faculty_id=faculty_a.id,
                    course_id=course_a.id,
                    rating=5,
                    comments="A course feedback.",
                ),
                FacultyFeedback(
                    student_id=student_b.id,
                    faculty_id=faculty_b.id,
                    course_id=course_b.id,
                    rating=1,
                    comments="B private student feedback.",
                ),
            ]
        )
        session.commit()

        return {
            "student_a": student_a.id,
            "student_b": student_b.id,
            "faculty_a": faculty_a.id,
            "faculty_b": faculty_b.id,
            "course_a": course_a.id,
            "course_b": course_b.id,
        }


def test_student_a_cannot_access_student_b_data(client, database):
    records = student_portal_records(database)
    login = client.post(
        "/auth/login",
        json={"email": "student.a@demo.invalid", "password": "StudentPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    dashboard = client.get("/student/dashboard", headers=headers)
    journey = client.get("/student/journey", headers=headers)
    feedback = client.get("/student/feedback", headers=headers)

    assert dashboard.status_code == journey.status_code == feedback.status_code == 200
    dashboard_json = dashboard.json()
    assert dashboard_json["enrolled_courses"] == 1
    assert [course["code"] for course in dashboard_json["courses"]] == ["PORTAL101"]
    assert dashboard_json["attendance_percentage"] == 50.0
    assert dashboard_json["marks_percentage"] == 80.0
    assert dashboard_json["risk"]["level"] == "medium"

    journey_text = str(journey.json())
    assert "PORTAL101" in journey_text
    assert "PRIVATE202" not in journey_text
    assert "B private" not in journey_text

    feedback_json = feedback.json()
    assert [item["message"] for item in feedback_json["received"]] == ["A feedback only."]
    assert [item["comments"] for item in feedback_json["submitted"]] == ["A course feedback."]
    assert "B private" not in str(feedback_json)

    forged_feedback = client.post(
        "/student/feedback",
        headers=headers,
        json={
            "student_id": records["student_b"],
            "faculty_id": records["faculty_a"],
            "course_id": records["course_a"],
            "rating": 5,
        },
    )
    assert forged_feedback.status_code == 422


def test_feedback_submission_uses_authenticated_student_and_enrollment(client, database):
    records = student_portal_records(database)
    login = client.post(
        "/auth/login",
        json={"email": "student.a@demo.invalid", "password": "StudentPass123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    accepted = client.post(
        "/student/feedback",
        headers=headers,
        json={
            "faculty_id": records["faculty_a"],
            "course_id": records["course_a"],
            "rating": 4,
            "comments": "Helpful, thanks.",
        },
    )
    forbidden_course = client.post(
        "/student/feedback",
        headers=headers,
        json={
            "faculty_id": records["faculty_b"],
            "course_id": records["course_b"],
            "rating": 4,
            "comments": "A different student's course.",
        },
    )

    assert accepted.status_code == 201
    assert forbidden_course.status_code == 404

    with database() as session:
        saved_feedback = session.get(FacultyFeedback, accepted.json()["id"])
        assert saved_feedback is not None
        assert saved_feedback.student_id == records["student_a"]
