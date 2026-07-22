"""Integration tests for POST /api/v1/scan/ with a mocked inference service."""

import io
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from nutrition.models import Food, FoodNutrient, Nutrient, PortionUnit, VisionClass
from PIL import Image
from rest_framework.test import APIClient

ClassifyFn = Callable[..., Awaitable[dict[str, Any]]]


def _seed_samosa() -> None:
    food = Food.objects.create(
        source="USDA", source_id="2708730", name="Samosa", food_group="FNDDS survey food"
    )
    amounts = {"energy_kcal": "310", "protein_g": "5", "carb_g": "32", "fat_g": "17"}
    for key, amount in amounts.items():
        nutrient = Nutrient.objects.create(key_name=key, display_name=key, unit="g")
        FoodNutrient.objects.create(food=food, nutrient=nutrient, amount_per_100g=amount)
    vision_class = VisionClass.objects.create(label="samosa", food=food, match_quality="exact")
    PortionUnit.objects.create(
        vision_class=vision_class, unit="piece", grams="100", is_default=True
    )


def _jpeg() -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 140, 60)).save(buf, "JPEG")
    return SimpleUploadedFile("food.jpg", buf.getvalue(), content_type="image/jpeg")


def _fake_classify(predictions: list[dict[str, Any]]) -> ClassifyFn:
    async def _classify(image_bytes: bytes, filename: str, top_k: int = 3) -> dict[str, Any]:
        return {"model_version": "baseline_v1", "predictions": predictions}

    return _classify


@pytest.fixture
def auth_client() -> APIClient:
    cache.clear()
    _seed_samosa()
    user = get_user_model().objects.create_user(email="diner@example.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_scan_returns_srs_shape(auth_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scans.views.classify",
        _fake_classify(
            [
                {"label": "samosa", "confidence": 0.9},
                {"label": "kachori", "confidence": 0.05},
                {"label": "pakora", "confidence": 0.03},
            ]
        ),
    )
    resp = auth_client.post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"scan_id", "model_version", "needs_confirmation", "items", "candidates"}
    assert body["model_version"] == "baseline_v1"
    assert body["needs_confirmation"] is False

    item = body["items"][0]
    assert item["label"] == "samosa"
    assert item["portion"] == {"unit": "piece", "grams": 100, "adjustable": True}
    kcal = item["nutrition"]["kcal"]
    assert kcal["min"] < 310 < kcal["max"]  # point 310, ±band range
    assert item["nutrition"]["source"] == "USDA"

    candidates = body["candidates"]
    assert len(candidates) == 3
    # The mapped candidate carries portion + nutrition (used by the low-confidence
    # picker); unmapped candidates degrade to just label + confidence.
    assert candidates[0]["label"] == "samosa"
    assert candidates[0]["nutrition"]["source"] == "USDA"
    assert candidates[0]["portion"]["unit"] == "piece"
    assert "nutrition" not in candidates[1]  # kachori is unmapped


@pytest.mark.django_db
def test_scan_flags_low_confidence(auth_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scans.views.classify", _fake_classify([{"label": "samosa", "confidence": 0.4}])
    )
    resp = auth_client.post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    assert resp.status_code == 200
    assert resp.json()["needs_confirmation"] is True


@pytest.mark.django_db
def test_scan_requires_auth() -> None:
    resp = APIClient().post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_scan_missing_image(auth_client: APIClient) -> None:
    assert auth_client.post("/api/v1/scan/", {}, format="multipart").status_code == 400


@pytest.mark.django_db
def test_scan_inference_unavailable(
    auth_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _boom(image_bytes: bytes, filename: str, top_k: int = 3) -> dict[str, Any]:
        raise httpx.ConnectError("down")

    monkeypatch.setattr("scans.views.classify", _boom)
    resp = auth_client.post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    assert resp.status_code == 502
