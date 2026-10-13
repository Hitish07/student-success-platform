"""Student doubts: question and answer schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


QuestionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=2000),
]


SubjectCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=16)]


class DoubtAsk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_code: SubjectCode
    question: QuestionText


class DoubtView(BaseModel):
    id: int
    subject_id: int
    subject_code: str
    subject_name: str
    question: str
    answer: str
    created_at: datetime


class DoubtList(BaseModel):
    doubts: list[DoubtView]
    remaining_today: int
