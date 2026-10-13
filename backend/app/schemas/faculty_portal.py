from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing import Annotated


class FacultySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
AssessmentTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class FacultyCourse(FacultySchema):
    id: int
    code: str
    name: str
    credits: int
    enrolled_students: int


class FacultyDashboard(FacultySchema):
    courses: list[FacultyCourse]
    assigned_students: int
    at_risk_students: int
    open_alerts: int


class FacultyStudent(FacultySchema):
    id: int
    full_name: str
    email: str
    attendance_percentage: float | None
    marks_percentage: float | None
    latest_risk_level: Literal["low", "medium", "high"] | None


class AssessmentCreate(FacultySchema):
    title: AssessmentTitle
    assessment_type: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    max_score: Decimal = Field(gt=0, le=99999.99)
    due_date: date


class AssessmentView(FacultySchema):
    id: int
    course_id: int
    title: str
    assessment_type: str
    max_score: Decimal
    due_date: date


AttendanceStatus = Literal["present", "absent", "late", "excused"]


class AttendanceEntry(FacultySchema):
    student_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    class_date: date
    status: AttendanceStatus


class AttendanceUpdate(FacultySchema):
    class_date: date
    status: AttendanceStatus


class AttendanceView(FacultySchema):
    id: int
    student_id: int
    student_name: str
    course_id: int
    course_code: str
    class_date: date
    status: AttendanceStatus


class MarkEntry(FacultySchema):
    student_id: int = Field(gt=0)
    assessment_id: int = Field(gt=0)
    score: Decimal = Field(ge=0, le=99999.99)
    is_submitted: bool = True


class MarkUpdate(FacultySchema):
    score: Decimal = Field(ge=0, le=99999.99)
    is_submitted: bool = True


class MarkView(FacultySchema):
    id: int
    student_id: int
    student_name: str
    assessment_id: int
    assessment_title: str
    max_score: Decimal
    score: Decimal
    is_submitted: bool
    submitted_at: datetime | None


class StudentNoteCreate(FacultySchema):
    student_id: int = Field(gt=0)
    content: NonBlank


class StudentNoteUpdate(FacultySchema):
    content: NonBlank


class StudentNoteView(FacultySchema):
    id: int
    student_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime


class InterventionCreate(FacultySchema):
    student_id: int = Field(gt=0)
    intervention_type: Literal["mentoring", "remedial_class", "counseling_referral"]
    description: NonBlank
    start_date: date


class InterventionView(FacultySchema):
    id: int
    student_id: int
    intervention_type: str
    description: str
    start_date: date
    status: Literal["assigned", "in_progress", "completed", "cancelled"]


class RiskFactorView(FacultySchema):
    key: str
    observation: str


class AtRiskStudent(FacultySchema):
    student_id: int
    student_name: str
    course_codes: list[str]
    risk_score: float
    risk_level: Literal["low", "medium", "high"]
    contributing_factors: list[RiskFactorView]
    open_alerts: int


class AlertView(FacultySchema):
    id: int
    student_id: int
    student_name: str
    course_codes: list[str]
    alert_type: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "acknowledged", "resolved"]
    created_at: datetime


class FacultyFeedbackView(FacultySchema):
    id: int
    student_name: str
    course_name: str | None
    rating: int
    comments: str | None
    submitted_at: datetime


class SuccessResponse(FacultySchema):
    id: int
    message: Literal["Saved."]


class CreatedResponse(FacultySchema):
    id: int
