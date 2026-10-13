"""Placement record schemas.

Faculty create placements for students in their own subjects. The principal
sees only aggregates. No student PII leaks to the principal view.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


CompanyName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]
RoleName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]

PlacementStatus = Literal["offered", "accepted", "declined", "joined"]


class PlacementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int = Field(gt=0)
    company: CompanyName
    role: RoleName
    package_lpa: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=6,
        decimal_places=2,
    )
    offer_date: date
    status: PlacementStatus = "offered"


class PlacementView(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_email: str
    company: str
    role: str
    package_lpa: float | None
    offer_date: date
    status: str
    created_at: datetime


class PlacementCreateResponse(BaseModel):
    id: int
    message: str


class PlacementTrendPoint(BaseModel):
    label: str
    value: float


class PlacementTrend(BaseModel):
    points: list[PlacementTrendPoint]
    total_placed: int
    placement_rate: float
    note: str
