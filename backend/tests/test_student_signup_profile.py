HEADERS = "Authorization"


def _payload(departments, **overrides):
    payload = {
        "email": "signup.profile@example.invalid",
        "full_name": "Signup Profile",
        "password": "LongDemoPassword123!",
        "department_id": departments[0]["id"],
        "year": 2,
        "semester": 1,
    }
    payload.update(overrides)
    return payload


def test_new_student_gets_profile_with_chosen_year_and_semester(client, demo_users):
    departments = client.get("/auth/departments").json()
    response = client.post("/auth/register", json=_payload(departments))
    assert response.status_code == 201
    headers = {HEADERS: f"Bearer {response.json()['access_token']}"}

    profile = client.get("/student/profile", headers=headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["year"] == 2
    assert body["semester"] == 1
    assert body["department_id"] == departments[0]["id"]

    subjects = client.get("/student/subjects", headers=headers)
    assert subjects.status_code == 200


def test_student_registration_rejects_invalid_year_or_semester(client, demo_users):
    departments = client.get("/auth/departments").json()
    assert client.post("/auth/register", json=_payload(departments, year=5)).status_code == 422
    assert client.post("/auth/register", json=_payload(departments, semester=3)).status_code == 422
    missing = _payload(departments)
    del missing["year"]
    assert client.post("/auth/register", json=missing).status_code == 422
