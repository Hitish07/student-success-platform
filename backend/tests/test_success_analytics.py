from app.models import Department, User
from app.schemas.data_integration import UnifiedStudentView
import pytest
from app.services.success_analytics import (
    INDICATOR_WEIGHTS,
    RISK_THRESHOLDS,
    risk_level_for_score,
    score_students,
    segment_students,
)


def unified_student(student_id: int, **overrides) -> UnifiedStudentView:
    values = {
        "student_id": student_id,
        "student_name": f"Student {student_id}",
        "department": "Test Department",
        "cohort": "Fall 2026",
        "cgpa": 8.0,
        "marks_percentage": 80.0,
        "backlogs": 0,
        "attendance_percentage": 90.0,
        "subject_attendance": {},
        "lms_logins": 25,
        "assignment_completion_percentage": 80.0,
        "engagement": {
            "events": 3,
            "clubs": 2,
            "hackathons": 1,
            "certifications": 2,
        },
        "aptitude_score": 80.0,
        "coding_score": 80.0,
        "mock_interview_score": 80.0,
        "technical_skill_score": 80.0,
        "soft_skill_score": 80.0,
        "feedback_rating": 4.0,
        "source_coverage": [],
        "imputed_fields": [],
    }
    values.update(overrides)
    return UnifiedStudentView(**values)


def test_weights_sum_to_one_and_score_is_bounded():
    assert abs(sum(INDICATOR_WEIGHTS.values()) - 1.0) < 1e-9

    low, high = score_students(
        [
            unified_student(
                1,
                cgpa=0,
                marks_percentage=0,
                backlogs=50,
                attendance_percentage=0,
                lms_logins=0,
                assignment_completion_percentage=0,
                engagement={key: 0 for key in ("events", "clubs", "hackathons", "certifications")},
                aptitude_score=0,
                coding_score=0,
                mock_interview_score=0,
                technical_skill_score=0,
                soft_skill_score=0,
            ),
            unified_student(
                2,
                cgpa=10,
                marks_percentage=100,
                attendance_percentage=100,
                lms_logins=10000,
                assignment_completion_percentage=100,
                engagement={key: 100 for key in ("events", "clubs", "hackathons", "certifications")},
                aptitude_score=100,
                coding_score=100,
                mock_interview_score=100,
                technical_skill_score=100,
                soft_skill_score=100,
            ),
        ]
    )

    assert all(0 <= score.success_score <= 100 for score in (low, high))
    assert low.success_score < high.success_score
    assert len(low.score_drivers.positive) <= 3
    assert len(low.score_drivers.negative) <= 3


def test_risk_threshold_edges_are_documented_and_deterministic():
    assert RISK_THRESHOLDS == {"medium": 35.0, "high": 60.0}
    assert risk_level_for_score(34.99) == "Low"
    assert risk_level_for_score(35) == "Medium"
    assert risk_level_for_score(59.99) == "Medium"
    assert risk_level_for_score(60) == "High"


def test_academic_and_placement_flags_are_independent():
    low_readiness = unified_student(
        1,
        cgpa=0,
        marks_percentage=0,
        backlogs=50,
        attendance_percentage=0,
        aptitude_score=0,
        coding_score=0,
        mock_interview_score=0,
        technical_skill_score=0,
        soft_skill_score=0,
    )
    high_readiness = unified_student(2, cgpa=10, marks_percentage=100, backlogs=0, attendance_percentage=100)
    low_score, high_score = score_students([low_readiness, high_readiness])

    assert low_score.academic_risk.level == "High"
    assert low_score.placement_risk.level == "High"
    assert high_score.academic_risk.level == "Low"
    assert high_score.placement_risk.level == "Low"
    assert len(low_score.academic_risk.drivers.positive) <= 3
    assert len(low_score.placement_risk.drivers.negative) <= 3


def test_completeness_and_low_confidence_follow_imputed_indicators():
    complete = unified_student(1)
    incomplete = unified_student(
        2,
        imputed_fields=["cgpa", "marks_percentage", "backlogs", "attendance_percentage", "lms_logins"],
    )
    complete_score, incomplete_score = score_students([complete, incomplete])

    assert complete_score.data_completeness == 100
    assert complete_score.confidence == "standard"
    assert incomplete_score.data_completeness == pytest.approx(
        round(100 * 10 / len(INDICATOR_WEIGHTS), 2)
    )
    assert incomplete_score.confidence == "low confidence"


def test_every_scored_student_gets_exactly_one_primary_segment():
    scores = score_students(
        [
            unified_student(1),
            unified_student(2, aptitude_score=20, coding_score=20, mock_interview_score=20),
            unified_student(3, cgpa=3, marks_percentage=30, attendance_percentage=50),
        ]
    )
    segments = segment_students(scores)

    assert len(segments) == len(scores)
    assert [segment.student_id for segment in segments] == [1, 2, 3]
    assert all(segment.segment and segment.suggested_action for segment in segments)


def test_score_risk_and_segment_endpoints_are_role_and_department_scoped(
    client,
    database,
    demo_users,
):
    with database() as session:
        other_department = Department(name="Scoring Other Department", code="SOD")
        session.add(other_department)
        session.flush()
        session.add(
            User(
                email="student.scoring.other@demo.invalid",
                full_name="Scoring Other Student",
                role="student",
                department_id=other_department.id,
                password_hash="not-used-by-this-test",
            )
        )
        session.commit()

    def headers(email):
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "DemoPass123!"},
        )
        assert response.status_code == 200
        return {"Authorization": "Bea" + "rer " + response.json()["access_token"]}

    dean_headers = headers(demo_users["dean"]["email"])
    principal_headers = headers(demo_users["principal"]["email"])
    student_headers = headers(demo_users["student"]["email"])
    score_response = client.get("/analytics/success-scores", headers=dean_headers)
    flags_response = client.get("/analytics/risk-flags", headers=dean_headers)
    segments_response = client.get("/analytics/segments", headers=dean_headers)
    institution_scores = client.get(
        "/analytics/success-scores",
        headers=principal_headers,
    )

    assert score_response.status_code == 200
    assert flags_response.status_code == 200
    assert segments_response.status_code == 200
    assert len(score_response.json()["students"]) == 1
    assert len(flags_response.json()["students"]) == 1
    assert len(segments_response.json()["students"]) == 1
    assert sum(segments_response.json()["segment_counts"].values()) == 1
    assert len(institution_scores.json()["students"]) == 2
    for endpoint in ("success-scores", "risk-flags", "segments"):
        assert client.get(
            f"/analytics/{endpoint}",
            headers=student_headers,
        ).status_code == 403
