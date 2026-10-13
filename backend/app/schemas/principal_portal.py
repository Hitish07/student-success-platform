"""Principal portal schemas: institution-level trends and an AI summary.

All read-only, all anonymous at the department level. No student PII is
returned. This module is a starting point for the principal dashboard.
"""

from pydantic import BaseModel


class TrendPoint(BaseModel):
    label: str
    value: float


class SeriesLine(BaseModel):
    name: str
    points: list[TrendPoint]


class AcademicTrend(BaseModel):
    institution: list[TrendPoint]
    by_department: list[SeriesLine]
    overall_average: float


class PlacementReadinessTrend(BaseModel):
    points: list[TrendPoint]
    overall_average: float
    note: str


class PrincipalDashboard(BaseModel):
    total_students: int
    average_attendance: float
    average_marks: float
    academic_trend: AcademicTrend
    placement_readiness: PlacementReadinessTrend
    ai_summary: str | None
