import pytest
from rest_framework.test import APIClient

CREDS = {"email": "diner@example.com", "password": "sup3rSecret!pw"}


@pytest.mark.django_db
def test_register_login_and_me() -> None:
    client = APIClient()

    reg = client.post("/api/v1/auth/register/", CREDS, format="json")
    assert reg.status_code == 201
    assert reg.json()["email"] == CREDS["email"]
    assert "password" not in reg.json()

    token = client.post("/api/v1/auth/token/", CREDS, format="json")
    assert token.status_code == 200
    access = token.json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["email"] == CREDS["email"]
    assert me.json()["daily_calorie_goal"] == 2000
    assert me.json()["data_consent"] is False


@pytest.mark.django_db
def test_me_requires_auth() -> None:
    assert APIClient().get("/api/v1/auth/me/").status_code == 401


def _auth_client() -> APIClient:
    client = APIClient()
    client.post("/api/v1/auth/register/", CREDS, format="json")
    access = client.post("/api/v1/auth/token/", CREDS, format="json").json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.mark.django_db
def test_update_goal_and_consent() -> None:
    client = _auth_client()
    resp = client.patch(
        "/api/v1/auth/me/", {"daily_calorie_goal": 2400, "data_consent": True}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["daily_calorie_goal"] == 2400
    assert resp.json()["data_consent"] is True
    # email is read-only — a PATCH must not change it.
    assert (
        client.patch("/api/v1/auth/me/", {"email": "x@y.z"}, format="json").json()["email"]
        == (CREDS["email"])
    )


@pytest.mark.django_db
def test_reject_out_of_range_goal() -> None:
    client = _auth_client()
    low = client.patch("/api/v1/auth/me/", {"daily_calorie_goal": 100}, format="json")
    high = client.patch("/api/v1/auth/me/", {"daily_calorie_goal": 99999}, format="json")
    assert low.status_code == 400
    assert high.status_code == 400


@pytest.mark.django_db
def test_token_refresh() -> None:
    client = APIClient()
    client.post("/api/v1/auth/register/", CREDS, format="json")
    refresh = client.post("/api/v1/auth/token/", CREDS, format="json").json()["refresh"]

    refreshed = client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert refreshed.status_code == 200
    assert "access" in refreshed.json()
