from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing import Annotated


class StudentPortalSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudentCourse(StudentPortalSchema):
    course_id: int
    code: str
    name: str
    credits: int
    faculty_id: int
    faculty_name: str
    attendance_percentage: float | None
    marks_percentage: float | None
    completed_assessments: int
    total_assessments: int


class RiskFactor(StudentPortalSchema):
    key: str
    label: str
    observation: str
    contribution: float


class PersonalRisk(StudentPortalSchema):
    score: float
    level: Literal["low", "medium", "high"]
    computed_at: datetime
    contributing_factors: list[RiskFactor]


class StudentDashboard(StudentPortalSchema):
    attendance_percentage: float | None
    marks_percentage: float | None
    enrolled_courses: int
    courses: list[StudentCourse]
    risk: PersonalRisk | None


class JourneyEvent(StudentPortalSchema):
    occurred_at: datetime
    event_type: str
    title: str
    description: str


class StudentJourney(StudentPortalSchema):
    events: list[JourneyEvent]


class FeedbackReceived(StudentPortalSchema):
    id: int
    faculty_name: str
    course_name: str | None
    message: str
    created_at: datetime


class FeedbackGiven(StudentPortalSchema):
    id: int
    faculty_name: str
    course_name: str
    rating: int
    comments: str | None
    submitted_at: datetime


class StudentFeedbackResponse(StudentPortalSchema):
    received: list[FeedbackReceived]
    submitted: list[FeedbackGiven]


Comments = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class FacultyCourseFeedback(StudentPortalSchema):
    faculty_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comments: Comments | None = None


class FeedbackSubmission(StudentPortalSchema):
    id: int
    message: Literal["Feedback submitted."]
