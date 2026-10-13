from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://student_success:change_me_for_local_development"
        "@localhost:5432/student_success"
    )
    jwt_secret: str = Field(
        default="replace-this-development-key-before-deployment",
        min_length=32,
        alias="JWT_SECRET",
    )
    jwt_secret_key: str = Field(
        default="replace-this-development-key-before-deployment",
        min_length=32,
        alias="JWT_SECRET_KEY",
    )
    principal_email: str = Field(default="principal@demo.invalid", alias="PRINCIPAL_EMAIL")
    principal_password: str = Field(default="DemoPass123!", alias="PRINCIPAL_PASSWORD")
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    frontend_origin: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
