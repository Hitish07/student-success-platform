import random

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import (
    AcademicSourceRecord,
    AttendanceSourceRecord,
    EngagementSourceRecord,
    FeedbackSourceRecord,
    LmsSourceRecord,
    PlacementSourceRecord,
    SkillsSourceRecord,
    User,
)
from app.seed import SEED, _seed_integration_sources

SOURCE_MODELS = (
    AcademicSourceRecord,
    AttendanceSourceRecord,
    LmsSourceRecord,
    EngagementSourceRecord,
    PlacementSourceRecord,
    SkillsSourceRecord,
    FeedbackSourceRecord,
)


def seed_integration_sources() -> None:
    with SessionLocal() as session:
        if any(
            session.scalar(select(func.count()).select_from(model))
            for model in SOURCE_MODELS
        ):
            raise RuntimeError(
                "Integration source tables are not empty; refusing to duplicate demo data."
            )
        students = list(
            session.scalars(select(User).where(User.role == "student").order_by(User.id))
        )
        if not students:
            raise RuntimeError("Seed the institution and students before integration sources.")
        _seed_integration_sources(session, students, random.Random(SEED))
        session.commit()
        print(f"Seeded fictional integration data for {len(students)} students.")
        print("Source data intentionally includes missing, duplicate, malformed, and out-of-range values.")


if __name__ == "__main__":
    seed_integration_sources()
