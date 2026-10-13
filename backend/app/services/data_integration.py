import math
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from statistics import median
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import data_integration as repository
from app.models import User
from app.schemas.data_integration import (
    DataIntegrationResult,
    DataQualityReport,
    UnifiedStudentView,
)

ENGAGEMENT_KEYS = ("events", "clubs", "hackathons", "certifications")
METRIC_RANGES: dict[str, tuple[float, float, bool]] = {
    "cgpa": (0, 10, False),
    "marks_percentage": (0, 100, False),
    "backlogs": (0, 50, True),
    "attendance_percentage": (0, 100, False),
    "lms_logins": (0, 10000, True),
    "assignment_completion_percentage": (0, 100, False),
    "aptitude_score": (0, 100, False),
    "coding_score": (0, 100, False),
    "mock_interview_score": (0, 100, False),
    "technical_skill_score": (0, 100, False),
    "soft_skill_score": (0, 100, False),
    "feedback_rating": (1, 5, False),
    **{f"engagement.{key}": (0, 100, True) for key in ENGAGEMENT_KEYS},
}


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.strip().upper())


def _identity_lookup(students: list[User]) -> dict[str, User]:
    identities: dict[str, User] = {}
    for student in students:
        candidates = (
            f"STU-{student.id:06d}",
            f"student-{student.id}",
            str(student.id),
        )
        for candidate in candidates:
            identities[_normalize_identifier(candidate)] = student
    return identities


def _validated(value: Any, metric: str, report: dict[str, int]) -> float | int | None:
    if value is None:
        return None
    minimum, maximum, integer = METRIC_RANGES[metric]
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        report["out_of_range_values"] += 1
        return None
    if not math.isfinite(numeric) or numeric < minimum or numeric > maximum:
        report["out_of_range_values"] += 1
        return None
    if integer and not numeric.is_integer():
        report["out_of_range_values"] += 1
        return None
    return int(numeric) if integer else numeric


def build_data_integration(
    db: Session,
    department_id: int | None = None,
) -> DataIntegrationResult:
    all_students = repository.students(db)
    students = (
        [student for student in all_students if student.department_id == department_id]
        if department_id is not None
        else all_students
    )
    student_ids = [student.id for student in students]
    identity_lookup = _identity_lookup(all_students)
    departments = repository.departments(db)
    cohorts = repository.cohorts(db, student_ids)
    grouped: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, int, str]] = set()
    report = {
        "rows_ingested": 0,
        "rows_cleaned": 0,
        "nulls_imputed": 0,
        "duplicates_removed": 0,
        "out_of_range_values": 0,
        "unresolved_rows": 0,
        "invalid_rows": 0,
    }
    source_rows: dict[str, int] = {}
    cleaned_source_rows: dict[str, int] = {}
    before_after_example: dict[str, Any] | None = None

    def process_source(
        source_name: str,
        rows: Iterable[Any],
        logical_key: Callable[[Any], str],
        extract: Callable[[Any], dict[str, Any]],
    ) -> None:
        nonlocal before_after_example
        materialized = list(rows)
        source_rows[source_name] = 0
        cleaned = 0
        for row in materialized:
            student = identity_lookup.get(_normalize_identifier(row.external_student_id))
            if student is None:
                if department_id is None:
                    source_rows[source_name] += 1
                    report["rows_ingested"] += 1
                    report["unresolved_rows"] += 1
                continue
            if department_id is not None and student.department_id != department_id:
                continue
            source_rows[source_name] += 1
            report["rows_ingested"] += 1
            key = (source_name, student.id, logical_key(row))
            row_key = logical_key(row)
            if source_name == "engagement" and row_key not in ENGAGEMENT_KEYS:
                report["invalid_rows"] += 1
                continue
            if key in seen:
                report["duplicates_removed"] += 1
                continue
            seen.add(key)
            values = extract(row)
            raw_values = {
                metric: float(value) if value is not None else None
                for metric, value in values.items()
            }
            for metric, value in values.items():
                values[metric] = _validated(value, metric, report)
            if before_after_example is None and raw_values != values:
                before_after_example = {
                    "source": source_name,
                    "external_student_id": row.external_student_id,
                    "canonical_student_id": student.id,
                    "before": raw_values,
                    "after": values,
                }
            grouped[student.id][source_name].append(
                {"key": row_key, "values": values}
            )
            cleaned += 1
        cleaned_source_rows[source_name] = cleaned
        report["rows_cleaned"] += cleaned

    process_source(
        "academic",
        repository.academic_records(db),
        lambda row: row.term.strip().casefold() if row.term else "unspecified",
        lambda row: {
            "cgpa": row.cgpa,
            "marks_percentage": row.marks_percentage,
            "backlogs": row.backlog_count,
        },
    )
    process_source(
        "attendance",
        repository.attendance_records(db),
        lambda row: (row.subject_code or "").strip().upper() or "OVERALL",
        lambda row: {"attendance_percentage": row.attendance_percentage},
    )
    process_source(
        "lms",
        repository.lms_records(db),
        lambda row: "activity",
        lambda row: {
            "lms_logins": row.login_count,
            "assignment_completion_percentage": row.assignment_completion_percentage,
        },
    )
    process_source(
        "engagement",
        repository.engagement_records(db),
        lambda row: row.activity_type.strip().lower(),
        lambda row: {f"engagement.{row.activity_type.strip().lower()}": row.activity_count},
    )
    process_source(
        "placement",
        repository.placement_records(db),
        lambda row: "assessment",
        lambda row: {
            "aptitude_score": row.aptitude_score,
            "coding_score": row.coding_score,
            "mock_interview_score": row.mock_interview_score,
        },
    )
    process_source(
        "skills",
        repository.skills_records(db),
        lambda row: "profile",
        lambda row: {
            "technical_skill_score": row.technical_score,
            "soft_skill_score": row.soft_skill_score,
        },
    )
    process_source(
        "feedback",
        repository.feedback_records(db),
        lambda row: row.category.strip().lower() if row.category else "general",
        lambda row: {"feedback_rating": row.rating},
    )

    per_student: dict[int, dict[str, float | int | None]] = {}
    attendance_codes = sorted(
        {
            record["key"]
            for records in grouped.values()
            for record in records["attendance"]
            if record["key"] != "OVERALL"
        }
    )
    for student in students:
        records = grouped[student.id]
        feature_values: dict[str, list[float | int]] = defaultdict(list)
        for source_name, source_records in records.items():
            for record in source_records:
                for metric, value in record["values"].items():
                    if metric != "attendance_percentage" and value is not None:
                        feature_values[metric].append(value)
        attendance_rows = records["attendance"]
        overall = [
            record["values"]["attendance_percentage"]
            for record in attendance_rows
            if record["key"] == "OVERALL"
            and record["values"]["attendance_percentage"] is not None
        ]
        if not overall:
            subject_values = [
                record["values"]["attendance_percentage"]
                for record in attendance_rows
                if record["key"] != "OVERALL"
                and record["values"]["attendance_percentage"] is not None
            ]
            if subject_values:
                feature_values["attendance_percentage"].append(
                    sum(subject_values) / len(subject_values)
                )
        else:
            feature_values["attendance_percentage"].extend(overall)

        values: dict[str, float | int | None] = {}
        for metric in METRIC_RANGES:
            if metric.startswith("engagement."):
                values[metric] = (
                    sum(feature_values[metric]) if feature_values[metric] else None
                )
            elif feature_values[metric]:
                values[metric] = float(median(feature_values[metric]))
            else:
                values[metric] = None
        for subject in attendance_codes:
            subject_values = [
                record["values"]["attendance_percentage"]
                for record in attendance_rows
                if record["key"] == subject
                and record["values"]["attendance_percentage"] is not None
            ]
            values[f"subject_attendance.{subject}"] = (
                float(median(subject_values)) if subject_values else None
            )
        per_student[student.id] = values

    all_metrics = list(METRIC_RANGES) + [
        f"subject_attendance.{subject}" for subject in attendance_codes
    ]
    imputation_values: dict[str, float | int] = {}
    for metric in all_metrics:
        present = [
            row[metric]
            for row in per_student.values()
            if row.get(metric) is not None
        ]
        if present:
            imputation_values[metric] = median(present)
        elif metric == "feedback_rating":
            imputation_values[metric] = 3
        else:
            imputation_values[metric] = 0

    unified: list[UnifiedStudentView] = []
    for student in students:
        values = per_student[student.id]
        imputed_fields = [
            metric
            for metric in METRIC_RANGES
            if values.get(metric) is None
        ]
        for metric in all_metrics:
            if values.get(metric) is None:
                values[metric] = imputation_values[metric]
                report["nulls_imputed"] += 1
            if metric in ("backlogs", "lms_logins") or metric.startswith("engagement."):
                values[metric] = int(round(float(values[metric] or 0)))
        engagement = {
            key: int(values[f"engagement.{key}"] or 0)
            for key in ENGAGEMENT_KEYS
        }
        subject_attendance = {
            subject: float(values[f"subject_attendance.{subject}"] or 0)
            for subject in attendance_codes
        }
        coverage = sorted(
            source_name
            for source_name, source_records in grouped[student.id].items()
            if source_records
        )
        unified.append(
            UnifiedStudentView(
                student_id=student.id,
                student_name=student.full_name,
                department=departments.get(student.department_id),
                cohort=cohorts.get(student.id),
                cgpa=float(values["cgpa"] or 0),
                marks_percentage=float(values["marks_percentage"] or 0),
                backlogs=int(values["backlogs"] or 0),
                attendance_percentage=float(values["attendance_percentage"] or 0),
                subject_attendance=subject_attendance,
                lms_logins=int(values["lms_logins"] or 0),
                assignment_completion_percentage=float(
                    values["assignment_completion_percentage"] or 0
                ),
                engagement=engagement,
                aptitude_score=float(values["aptitude_score"] or 0),
                coding_score=float(values["coding_score"] or 0),
                mock_interview_score=float(values["mock_interview_score"] or 0),
                technical_skill_score=float(values["technical_skill_score"] or 0),
                soft_skill_score=float(values["soft_skill_score"] or 0),
                feedback_rating=float(values["feedback_rating"] or 0),
                source_coverage=coverage,
                imputed_fields=imputed_fields,
            )
        )

    return DataIntegrationResult(
        students=unified,
        quality_report=DataQualityReport(
            **report,
            source_rows=source_rows,
            cleaned_source_rows=cleaned_source_rows,
            before_after_example=before_after_example,
        ),
    )
