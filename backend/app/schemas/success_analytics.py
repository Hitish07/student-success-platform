from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["Low", "Medium", "High"]
ConfidenceLabel = Literal["standard", "low confidence"]


class ScoreDriver(BaseModel):
    indicator: str
    student_value: float
    cohort_average: float
    contribution: float


class DriverSet(BaseModel):
    positive: list[ScoreDriver]
    negative: list[ScoreDriver]


class RiskFlag(BaseModel):
    level: RiskLevel
    risk_score: float = Field(ge=0, le=100)
    drivers: DriverSet


class StudentSuccessScore(BaseModel):
    student_id: int
    student_name: str
    department: str | None
    cohort: str | None
    success_score: float = Field(ge=0, le=100)
    academic_score: float = Field(ge=0, le=100)
    placement_score: float = Field(ge=0, le=100)
    engagement_score: float = Field(ge=0, le=100)
    academic_risk: RiskFlag
    placement_risk: RiskFlag
    score_drivers: DriverSet
    data_completeness: float = Field(ge=0, le=100)
    confidence: ConfidenceLabel
    imputed_fields: list[str]


class StudentSegment(BaseModel):
    student_id: int
    student_name: str
    department: str | None
    cohort: str | None
    segment: str
    suggested_action: str


class StudentRiskFlags(BaseModel):
    student_id: int
    student_name: str
    department: str | None
    cohort: str | None
    academic_risk: RiskFlag
    placement_risk: RiskFlag


class SuccessScoresResponse(BaseModel):
    students: list[StudentSuccessScore]


class RiskFlagsResponse(BaseModel):
    students: list[StudentRiskFlags]


class SegmentsResponse(BaseModel):
    students: list[StudentSegment]
    segment_counts: dict[str, int]
