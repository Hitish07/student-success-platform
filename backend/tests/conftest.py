import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import Department, User


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield testing_session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(database):
    def override_get_db():
        with database() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def demo_users(database):
    with database() as session:
        department = Department(name="Demo Department", code="DEMO")
        session.add(department)
        session.flush()
        users = {}
        for role, email in (
            ("student", "student.cs.001@demo.invalid"),
            ("faculty", "faculty.cs.1@demo.invalid"),
            ("dean", "dean.cs@demo.invalid"),
            ("principal", "principal@demo.invalid"),
        ):
            user = User(
                email=email,
                full_name=f"Demo {role.title()}",
                role=role,
                department_id=department.id,
                password_hash=hash_password("DemoPass123!"),
            )
            session.add(user)
            users[role] = user
        session.commit()
        return {role: {"id": user.id, "email": user.email} for role, user in users.items()}
