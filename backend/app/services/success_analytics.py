from math import isclose
from typing import Literal

from app.schemas.data_integration import UnifiedStudentView
from app.schemas.success_analytics import (
    DriverSet,
    RiskFlag,
    ScoreDriver,
    StudentSegment,
    StudentSuccessScore,
)

# Weights are the single source of truth; indicator values below are normalized to [0, 1].
INDICATOR_WEIGHTS: dict[str, float] = {
    "cgpa": 0.12,
    "marks_percentage": 0.12,
    "backlogs": 0.08,
    "attendance_percentage": 0.12,
    "lms_logins": 0.04,
    "assignment_completion_percentage": 0.06,
    "engagement.events": 0.02,
    "engagement.clubs": 0.02,
    "engagement.hackathons": 0.03,
    "engagement.certifications": 0.03,
    "aptitude_score": 0.07,
    "coding_score": 0.11,
    "mock_interview_score": 0.06,
    "technical_skill_score": 0.07,
    "soft_skill_score": 0.05,
}
INDICATOR_LABELS = {
    "cgpa": "CGPA",
    "marks_percentage": "Academic marks",
    "backlogs": "Backlog record",
    "attendance_percentage": "Attendance",
    "lms_logins": "LMS activity",
    "assignment_completion_percentage": "Assignment completion",
    "engagement.events": "Campus events",
    "engagement.clubs": "Club participation",
    "engagement.hackathons": "Hackathons",
    "engagement.certifications": "Certifications",
    "aptitude_score": "Placement aptitude",
    "coding_score": "Coding assessment",
    "mock_interview_score": "Mock interview",
    "technical_skill_score": "Technical skills",
    "soft_skill_score": "Soft skills",
}
INDICATOR_MAXIMA = {
    "cgpa": 10,
    "marks_percentage": 100,
    "backlogs": 50,
    "attendance_percentage": 100,
    "lms_logins": 50,
    "assignment_completion_percentage": 100,
    "engagement.events": 5,
    "engagement.clubs": 3,
    "engagement.hackathons": 2,
    "engagement.certifications": 3,
    "aptitude_score": 100,
    "coding_score": 100,
    "mock_interview_score": 100,
    "technical_skill_score": 100,
    "soft_skill_score": 100,
}
INVERTED_INDICATORS = frozenset({"backlogs"})
ACADEMIC_INDICATORS = (
    "cgpa",
    "marks_percentage",
    "backlogs",
    "attendance_percentage",
)
PLACEMENT_INDICATORS = (
    "aptitude_score",
    "coding_score",
    "mock_interview_score",
    "technical_skill_score",
    "soft_skill_score",
)
ENGAGEMENT_INDICATORS = (
    "engagement.events",
    "engagement.clubs",
    "engagement.hackathons",
    "engagement.certifications",
)
RISK_THRESHOLDS = {"medium": 35.0, "high": 60.0}
COMPLETENESS_INDICATORS = tuple(INDICATOR_WEIGHTS)

if not isclose(sum(INDICATOR_WEIGHTS.values()), 1.0, abs_tol=1e-9):
    raise RuntimeError("Success indicator weights must sum to 1.")


def _indicator_values(student: UnifiedStudentView) -> dict[str, float]:
    values = {
        "cgpa": student.cgpa,
        "marks_percentage": student.marks_percentage,
        "backlogs": student.backlogs,
        "attendance_percentage": student.attendance_percentage,
        "lms_logins": student.lms_logins,
        "assignment_completion_percentage": student.assignment_completion_percentage,
        "engagement.events": student.engagement["events"],
        "engagement.clubs": student.engagement["clubs"],
        "engagement.hackathons": student.engagement["hackathons"],
        "engagement.certifications": student.engagement["certifications"],
        "aptitude_score": student.aptitude_score,
        "coding_score": student.coding_score,
        "mock_interview_score": student.mock_interview_score,
        "technical_skill_score": student.technical_skill_score,
        "soft_skill_score": student.soft_skill_score,
    }
    normalized = {
        key: min(max(float(value) / INDICATOR_MAXIMA[key], 0), 1)
        for key, value in values.items()
    }
    for key in INVERTED_INDICATORS:
        normalized[key] = 1 - normalized[key]
    return normalized


def _weighted_category(
    values: dict[str, float],
    indicators: tuple[str, ...],
) -> float:
    weight_sum = sum(INDICATOR_WEIGHTS[key] for key in indicators)
    return sum(INDICATOR_WEIGHTS[key] * values[key] for key in indicators) / weight_sum


def _drivers(
    values: dict[str, float],
    cohort_average: dict[str, float],
    indicators: tuple[str, ...],
    *,
    risk_direction: bool = False,
) -> DriverSet:
    weight_sum = sum(INDICATOR_WEIGHTS[key] for key in indicators)
    contributions = []
    for key in indicators:
        student_value = 1 - values[key] if risk_direction else values[key]
        average = 1 - cohort_average[key] if risk_direction else cohort_average[key]
        contribution = (
            INDICATOR_WEIGHTS[key] / weight_sum * (student_value - average) * 100
        )
        contributions.append(
            ScoreDriver(
                indicator=INDICATOR_LABELS[key],
                student_value=round(student_value * 100, 2),
                cohort_average=round(average * 100, 2),
                contribution=round(contribution, 2),
            )
        )
    return DriverSet(
        positive=sorted(
            (driver for driver in contributions if driver.contribution > 0),
            key=lambda driver: (-driver.contribution, driver.indicator),
        )[:3],
        negative=sorted(
            (driver for driver in contributions if driver.contribution < 0),
            key=lambda driver: (driver.contribution, driver.indicator),
        )[:3],
    )


def _risk_flag(
    values: dict[str, float],
    cohort_average: dict[str, float],
    indicators: tuple[str, ...],
) -> RiskFlag:
    weight_sum = sum(INDICATOR_WEIGHTS[key] for key in indicators)
    risk_score = sum(
        INDICATOR_WEIGHTS[key] * (1 - values[key])
        for key in indicators
    ) / weight_sum
    level = risk_level_for_score(risk_score * 100)
    return RiskFlag(
        level=level,
        risk_score=round(risk_score * 100, 2),
        drivers=_drivers(
            values,
            cohort_average,
            indicators,
            risk_direction=True,
        ),
    )


def risk_level_for_score(risk_score: float) -> Literal["Low", "Medium", "High"]:
    if risk_score >= RISK_THRESHOLDS["high"]:
        return "High"
    if risk_score >= RISK_THRESHOLDS["medium"]:
        return "Medium"
    return "Low"


def score_students(
    students: list[UnifiedStudentView],
) -> list[StudentSuccessScore]:
    if not students:
        return []
    normalized = [_indicator_values(student) for student in students]
    cohort_average = {
        key: sum(values[key] for values in normalized) / len(normalized)
        for key in INDICATOR_WEIGHTS
    }
    scores: list[StudentSuccessScore] = []
    for student, values in zip(students, normalized):
        score = sum(
            INDICATOR_WEIGHTS[key] * values[key]
            for key in INDICATOR_WEIGHTS
        ) * 100
        completeness = (
            (len(COMPLETENESS_INDICATORS) - sum(
                key in student.imputed_fields for key in COMPLETENESS_INDICATORS
            ))
            / len(COMPLETENESS_INDICATORS)
            * 100
        )
        scores.append(
            StudentSuccessScore(
                student_id=student.student_id,
                student_name=student.student_name,
                department=student.department,
                cohort=student.cohort,
                success_score=round(min(max(score, 0), 100), 2),
                academic_score=round(_weighted_category(values, ACADEMIC_INDICATORS) * 100, 2),
                placement_score=round(_weighted_category(values, PLACEMENT_INDICATORS) * 100, 2),
                engagement_score=round(_weighted_category(values, ENGAGEMENT_INDICATORS) * 100, 2),
                academic_risk=_risk_flag(values, cohort_average, ACADEMIC_INDICATORS),
                placement_risk=_risk_flag(values, cohort_average, PLACEMENT_INDICATORS),
                score_drivers=_drivers(values, cohort_average, tuple(INDICATOR_WEIGHTS)),
                data_completeness=round(completeness, 2),
                confidence="low confidence" if completeness < 70 else "standard",
                imputed_fields=student.imputed_fields,
            )
        )
    return scores


def assign_segment(score: StudentSuccessScore) -> StudentSegment:
    if score.placement_score >= 75 and score.placement_risk.level == "Low":
        segment = "Placement-ready"
        action = "Offer advanced employer projects, interview practice, and placement opportunities."
    elif score.academic_score >= 70 and score.placement_score < 60:
        segment = "Strong academics, placement gap"
        action = "Provide aptitude and coding practice plus mock interviews."
    elif score.engagement_score >= 70 and score.academic_score < 60:
        segment = "Highly engaged, academic support needed"
        action = "Pair participation strengths with tutoring and a course recovery plan."
    elif score.engagement_score < 40 and (
        score.academic_risk.level == "High" or score.placement_risk.level == "High"
    ):
        segment = "Disengaged, elevated risk"
        action = "Arrange a supportive check-in and agree on a short, personalized action plan."
    else:
        segment = "Balanced development"
        weakest = min(
            (
                (score.academic_score, "academic"),
                (score.engagement_score, "engagement"),
                (score.placement_score, "placement readiness"),
            ),
            key=lambda item: item[0],
        )[1]
        action = f"Review the student's {weakest} needs and set one measurable next step."
    return StudentSegment(
        student_id=score.student_id,
        student_name=score.student_name,
        department=score.department,
        cohort=score.cohort,
        segment=segment,
        suggested_action=action,
    )


def segment_students(
    scores: list[StudentSuccessScore],
) -> list[StudentSegment]:
    return [assign_segment(score) for score in scores]
