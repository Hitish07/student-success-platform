import random
from decimal import Decimal

from app.seed import _seed_integration_sources
from app.models import (
    AcademicSourceRecord,
    AttendanceSourceRecord,
    Department,
    FeedbackSourceRecord,
    User,
)


def bearer_token(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "DemoPass123!"},
    )
    assert response.status_code == 200
    return {"Authorization": "Bea" + "rer " + response.json()["access_token"]}


def test_pipeline_normalizes_ids_deduplicates_validates_and_imputes(
    client,
    database,
    demo_users,
):
    student_id = demo_users["student"]["id"]
    with database() as session:
        session.add_all(
            [
                AcademicSourceRecord(
                    external_student_id=f"STU-{student_id:06d}",
                    cgpa=Decimal("8.25"),
                    marks_percentage=Decimal("81"),
                    backlog_count=1,
                ),
                AcademicSourceRecord(
                    external_student_id=f" student_{student_id} ",
                    cgpa=Decimal("9.50"),
                    marks_percentage=Decimal("90"),
                    backlog_count=0,
                ),
                AcademicSourceRecord(
                    external_student_id="STU-999999",
                    cgpa=Decimal("7.00"),
                    marks_percentage=None,
                    backlog_count=0,
                ),
                AttendanceSourceRecord(
                    external_student_id=f"stu_{student_id:06d}",
                    subject_code=None,
                    attendance_percentage=Decimal("72"),
                ),
                AttendanceSourceRecord(
                    external_student_id=str(student_id),
                    subject_code="CS101",
                    attendance_percentage=Decimal("65"),
                ),
                AttendanceSourceRecord(
                    external_student_id=f"STU-{student_id:06d}",
                    subject_code="CS101",
                    attendance_percentage=Decimal("95"),
                ),
                AttendanceSourceRecord(
                    external_student_id=f"STU-{student_id:06d}",
                    subject_code="CS102",
                    attendance_percentage=Decimal("140"),
                ),
                FeedbackSourceRecord(
                    external_student_id=f"STU-{student_id:06d}",
                    rating=Decimal("8"),
                    category="teaching",
                ),
            ]
        )
        session.commit()

    response = client.get(
        "/analytics/data-integration",
        headers=bearer_token(client, demo_users["principal"]["email"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["students"]) == 1
    student = payload["students"][0]
    assert student["student_id"] == student_id
    assert student["cgpa"] == 8.25
    assert student["marks_percentage"] == 81
    assert student["attendance_percentage"] == 72
    assert student["subject_attendance"]["CS101"] == 65
    assert student["subject_attendance"]["CS102"] == 0
    assert student["feedback_rating"] == 3
    assert set(student["source_coverage"]) == {"academic", "attendance", "feedback"}

    report = payload["quality_report"]
    assert report["rows_ingested"] == 8
    assert report["rows_cleaned"] == 5
    assert report["duplicates_removed"] == 2
    assert report["out_of_range_values"] == 2
    assert report["unresolved_rows"] == 1
    assert report["nulls_imputed"] > 0


def test_data_integration_endpoint_is_role_and_department_scoped(
    client,
    database,
    demo_users,
):
    with database() as session:
        other_department = Department(name="Other Integration Department", code="OID")
        session.add(other_department)
        session.flush()
        other_student = User(
            email="student.integration.other@demo.invalid",
            full_name="Other Department Student",
            role="student",
            department_id=other_department.id,
            password_hash="not-used-by-this-test",
        )
        session.add(other_student)
        session.flush()
        session.add(
            AcademicSourceRecord(
                external_student_id=f"STU-{other_student.id:06d}",
                cgpa=Decimal("6.50"),
                marks_percentage=Decimal("60"),
                backlog_count=2,
            )
        )
        session.commit()

    student_response = client.get(
        "/analytics/data-integration",
        headers=bearer_token(client, demo_users["student"]["email"]),
    )
    dean_response = client.get(
        "/analytics/data-integration",
        headers=bearer_token(client, demo_users["dean"]["email"]),
    )
    principal_response = client.get(
        "/analytics/data-integration",
        headers=bearer_token(client, demo_users["principal"]["email"]),
    )

    assert student_response.status_code == 403
    assert dean_response.status_code == 200
    assert len(dean_response.json()["students"]) == 1
    assert "Other Department Student" not in str(dean_response.json())
    assert principal_response.status_code == 200
    assert len(principal_response.json()["students"]) == 2


def test_demo_source_seed_contains_quality_defects(client, database, demo_users):
    student_id = demo_users["student"]["id"]
    with database() as session:
        student = session.get(User, student_id)
        _seed_integration_sources(session, [student], random.Random(20261012))
        session.commit()

    response = client.get(
        "/analytics/data-integration",
        headers=bearer_token(client, demo_users["principal"]["email"]),
    )

    assert response.status_code == 200
    report = response.json()["quality_report"]
    assert report["rows_ingested"] >= 20
    assert report["duplicates_removed"] >= 7
    assert report["unresolved_rows"] == 1
    assert report["out_of_range_values"] >= 8
    assert report["nulls_imputed"] > 0
