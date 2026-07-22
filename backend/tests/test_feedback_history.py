"""Tests for the v1 API surface added on top of /scan: feedback, logging, summary, search."""

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from nutrition.models import Food
from rest_framework.test import APIClient
from scans.models import Scan


def _user(email: str = "diner@example.com") -> Any:
    return get_user_model().objects.create_user(email=email, password="pw")


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _scan(user: Any, label: str = "samosa") -> Scan:
    return Scan.objects.create(user=user, label=label, confidence=0.9, model_version="baseline_v1")


@pytest.mark.django_db
def test_feedback_confirm_and_correct() -> None:
    user = _user()
    client = _client(user)
    scan = _scan(user)

    confirm = client.post(f"/api/v1/scan/{scan.id}/feedback/", {"confirmed": True}, format="json")
    assert confirm.status_code == 200
    assert confirm.json()["confirmed"] is True

    correct = client.post(
        f"/api/v1/scan/{scan.id}/feedback/",
        {"confirmed": False, "corrected_label": "kachori"},
        format="json",
    )
    assert correct.status_code == 200
    scan.refresh_from_db()
    assert scan.confirmed is False
    assert scan.corrected_label == "kachori"


@pytest.mark.django_db
def test_feedback_on_other_users_scan_is_404() -> None:
    owner = _user("owner@example.com")
    scan = _scan(owner)
    intruder_client = _client(_user("intruder@example.com"))
    resp = intruder_client.post(
        f"/api/v1/scan/{scan.id}/feedback/", {"confirmed": True}, format="json"
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_meal_log_create_and_list_is_user_scoped() -> None:
    user = _user()
    client = _client(user)
    payload = {"label": "samosa", "kcal": 310, "portion_grams": "100"}
    assert client.post("/api/v1/log/", payload, format="json").status_code == 201

    other_client = _client(_user("other@example.com"))
    other_client.post(
        "/api/v1/log/", {"label": "idli", "kcal": 96, "portion_grams": "75"}, format="json"
    )

    mine = client.get("/api/v1/log/")
    assert mine.status_code == 200
    labels = [row["label"] for row in mine.json()]
    assert labels == ["samosa"]


@pytest.mark.django_db
def test_daily_summary_totals_vs_goal() -> None:
    user = _user()
    client = _client(user)
    macros = {"protein_g": "5", "carbs_g": "30", "fat_g": "2"}
    for kcal in (310, 96, 250):
        client.post(
            "/api/v1/log/",
            {"label": "x", "kcal": kcal, "portion_grams": "100", **macros},
            format="json",
        )

    summary = client.get("/api/v1/log/summary/")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_kcal"] == 656
    assert body["goal"] == 2000
    assert body["remaining"] == 1344
    assert body["count"] == 3
    assert body["protein_g"] == 15.0  # 3 × 5
    assert body["carbs_g"] == 90.0
    assert body["fat_g"] == 6.0


@pytest.mark.django_db
def test_meal_log_rejects_negative_macros() -> None:
    client = _client(_user())
    resp = client.post(
        "/api/v1/log/",
        {"label": "x", "kcal": 100, "portion_grams": "50", "protein_g": "-5"},
        format="json",
    )
    assert resp.status_code == 400
    assert "protein_g" in resp.json()


@pytest.mark.django_db
def test_summary_rejects_malformed_date() -> None:
    client = _client(_user())
    resp = client.get("/api/v1/log/summary/", {"date": "2026-99-99"})
    assert resp.status_code == 400
    assert "date" in resp.json()

    # The list endpoint guards the same way.
    assert client.get("/api/v1/log/", {"date": "not-a-date"}).status_code == 400


@pytest.mark.django_db
def test_meal_log_delete_is_user_scoped() -> None:
    user = _user()
    client = _client(user)
    created = client.post(
        "/api/v1/log/", {"label": "samosa", "kcal": 310, "portion_grams": "100"}, format="json"
    )
    log_id = created.json()["id"]

    # A different user cannot delete it.
    intruder = _client(_user("intruder@example.com"))
    assert intruder.delete(f"/api/v1/log/{log_id}/").status_code == 404

    # The owner can.
    assert client.delete(f"/api/v1/log/{log_id}/").status_code == 204
    assert client.get("/api/v1/log/").json() == []


@pytest.mark.django_db
def test_food_search() -> None:
    Food.objects.create(source="USDA", source_id="1", name="Samosa", food_group="snack")
    Food.objects.create(source="IFCT", source_id="2", name="Apple, big", food_group="fruit")
    client = _client(_user())

    hit = client.get("/api/v1/foods/search/", {"q": "samos"})
    assert hit.status_code == 200
    assert [f["name"] for f in hit.json()] == ["Samosa"]

    assert client.get("/api/v1/foods/search/", {"q": ""}).json() == []
