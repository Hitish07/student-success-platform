from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Role = Literal["student", "faculty", "dean", "principal"]
EmailAddress = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudentRegistration(StrictSchema):
    email: EmailAddress
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=72)
    department_id: int = Field(gt=0)
    year: int = Field(ge=1, le=4)
    semester: int = Field(ge=1, le=2)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be blank.")
        return normalized

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class FacultyRegistration(StrictSchema):
    name: str = Field(min_length=1, max_length=160)
    email: EmailAddress
    password: str = Field(min_length=12, max_length=72)
    department_id: int = Field(gt=0)
    subject_ids: list[Annotated[int, Field(gt=0)]] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be blank.")
        return normalized

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value

    @field_validator("subject_ids")
    @classmethod
    def require_unique_subjects(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Select each subject only once.")
        return value


class LoginRequest(StrictSchema):
    email: EmailAddress
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class RefreshRequest(StrictSchema):
    refresh_token: str = Field(min_length=1, max_length=4096)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailAddress
    full_name: str
    role: Role
    department_id: int | None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str


class SubjectOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    year: int
    semester: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class PortalResponse(BaseModel):
    portal: Role
    message: str
    user: UserResponse
