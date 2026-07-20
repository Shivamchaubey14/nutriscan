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


@pytest.mark.django_db
def test_me_requires_auth() -> None:
    assert APIClient().get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db
def test_token_refresh() -> None:
    client = APIClient()
    client.post("/api/v1/auth/register/", CREDS, format="json")
    refresh = client.post("/api/v1/auth/token/", CREDS, format="json").json()["refresh"]

    refreshed = client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
    assert refreshed.status_code == 200
    assert "access" in refreshed.json()
