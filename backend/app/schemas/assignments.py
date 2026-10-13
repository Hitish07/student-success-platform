from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


AssignmentTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class FacultySubjectView(BaseModel):
    id: int
    code: str
    name: str
    year: int
    semester: int


class SubjectStudentView(BaseModel):
    id: int
    full_name: str
    email: str


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: int = Field(gt=0)
    title: AssignmentTitle
    description: str | None = Field(default=None, max_length=5000)
    due_date: date
    max_marks: Decimal = Field(gt=0, max_digits=8, decimal_places=2)


class FacultyAssignmentView(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    subject_name: str
    title: str
    description: str | None
    due_date: date
    max_marks: Decimal
    created_at: datetime


class StudentAssignmentView(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    subject_name: str
    title: str
    description: str | None
    due_date: date
    max_marks: Decimal
    status: Literal["open", "overdue", "submitted"]
    submitted_at: datetime | None
    answer_text: str | None = None
    marks: Decimal | None = None
    feedback: str | None = None


AnswerText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class AssignmentSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_text: AnswerText


class AssignmentSubmissionView(BaseModel):
    id: int
    assignment_id: int
    submitted_at: datetime


class GradeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marks: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    feedback: str | None = Field(default=None, max_length=5000)


class SubmissionGradingView(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    student_name: str
    student_email: str
    submitted_at: datetime
    answer_text: str | None
    marks: Decimal | None
    feedback: str | None
    max_marks: Decimal
