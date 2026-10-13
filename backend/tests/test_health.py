from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_default_vite_origins_and_alternate_loopback_port() -> None:
    client = TestClient(app)

    for origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ):
        response = client.options(
            "/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "authorization" in response.headers["access-control-allow-headers"].lower()
        assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_frontend_origin_setting_accepts_comma_separated_values() -> None:
    from app.core.config import Settings

    config = Settings(
        frontend_origin=" https://portal.example.invalid, http://127.0.0.1:5174 "
    )

    assert config.frontend_origins == [
        "https://portal.example.invalid",
        "http://127.0.0.1:5174",
    ]
