import jwt

from app.core.config import settings

DEMO_PASSWORD = "DemoPass123!"


def access_token(client, email):
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_grants_only_the_account_role(client, demo_users):
    for role, account in demo_users.items():
        token = access_token(client, account["email"])
        response = client.get(f"/portals/{role}", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["portal"] == role
        assert response.json()["user"]["id"] == account["id"]


def test_portals_require_authentication_and_matching_role(client, demo_users):
    assert client.get("/portals/student").status_code == 401

    token = access_token(client, demo_users["student"]["email"])
    response = client.get("/portals/principal", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_identity_comes_from_token_not_request_parameters(client, demo_users):
    token = access_token(client, demo_users["student"]["email"])
    response = client.get(
        f"/auth/me?user_id={demo_users['principal']['id']}&role=principal",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == demo_users["student"]["id"]
    assert response.json()["role"] == "student"


def test_role_claim_must_match_the_database_account(client, demo_users):
    token = access_token(client, demo_users["student"]["email"])
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        issuer="student-success-platform",
    )
    claims["role"] = "principal"
    forged_token = jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")

    response = client.get(
        "/portals/principal",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 401


def test_registration_creates_student_and_rejects_client_role(client, demo_users):
    department_response = client.get("/auth/departments")
    assert department_response.status_code == 200
    department_id = department_response.json()[0]["id"]
    payload = {
        "email": "new.student@example.invalid",
        "full_name": "New Student",
        "password": DEMO_PASSWORD,
        "department_id": department_id,
        "year": 2,
        "semester": 1,
    }

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "student"
    assert client.post("/auth/register", json={**payload, "role": "principal"}).status_code == 422
    assert client.post("/auth/register", json=payload).status_code == 409


def test_refresh_rotates_and_revokes_previous_token(client, demo_users):
    login = client.post(
        "/auth/login",
        json={"email": demo_users["student"]["email"], "password": DEMO_PASSWORD},
    )
    original_refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": original_refresh_token})

    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != original_refresh_token
    assert client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh_token},
    ).status_code == 401


def test_logout_revokes_refresh_token(client, demo_users):
    login = client.post(
        "/auth/login",
        json={"email": demo_users["student"]["email"], "password": DEMO_PASSWORD},
    )
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )

    assert response.status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401
