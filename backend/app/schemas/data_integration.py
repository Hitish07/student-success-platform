from typing import Any

from pydantic import BaseModel


class UnifiedStudentView(BaseModel):
    student_id: int
    student_name: str
    department: str | None
    cohort: str | None
    cgpa: float
    marks_percentage: float
    backlogs: int
    attendance_percentage: float
    subject_attendance: dict[str, float]
    lms_logins: int
    assignment_completion_percentage: float
    engagement: dict[str, int]
    aptitude_score: float
    coding_score: float
    mock_interview_score: float
    technical_skill_score: float
    soft_skill_score: float
    feedback_rating: float
    source_coverage: list[str]
    imputed_fields: list[str]


class DataQualityReport(BaseModel):
    rows_ingested: int
    rows_cleaned: int
    nulls_imputed: int
    duplicates_removed: int
    out_of_range_values: int
    unresolved_rows: int
    invalid_rows: int
    source_rows: dict[str, int]
    cleaned_source_rows: dict[str, int]
    before_after_example: dict[str, Any] | None


class DataIntegrationResult(BaseModel):
    students: list[UnifiedStudentView]
    quality_report: DataQualityReport
