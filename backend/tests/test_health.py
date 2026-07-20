import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_ok() -> None:
    resp = APIClient().get("/health/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] is True
