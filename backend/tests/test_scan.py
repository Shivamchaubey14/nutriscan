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


def _fake_classify(
    predictions: list[dict[str, Any]], regions: list[dict[str, Any]] | None = None
) -> ClassifyFn:
    async def _classify(image_bytes: bytes, filename: str, top_k: int = 3) -> dict[str, Any]:
        return {
            "model_version": "baseline_v1",
            "predictions": predictions,
            "regions": regions or [],
        }

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
def test_scan_multi_item_from_regions(
    auth_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-2: 2+ detected regions become one item each; duplicates and unmapped skip."""
    _seed_idli()

    def region(box: list[int], score: float, label: str, conf: float) -> dict[str, Any]:
        return {"box": box, "score": score, "predictions": [{"label": label, "confidence": conf}]}

    regions = [
        region([0, 0, 100, 100], 0.9, "samosa", 0.88),
        {"box": [50, 50, 60, 60], "score": 0.85, "predictions": []},  # malformed: no preds
        region([120, 0, 220, 100], 0.8, "idli", 0.7),
        region([0, 120, 100, 220], 0.7, "samosa", 0.6),  # duplicate label
        region([120, 120, 220, 220], 0.6, "unmapped", 0.5),  # not in nutrition DB
    ]
    monkeypatch.setattr(
        "scans.views.classify",
        _fake_classify([{"label": "samosa", "confidence": 0.88}], regions=regions),
    )
    resp = auth_client.post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    assert resp.status_code == 200
    items = resp.json()["items"]
    # duplicate samosa collapsed, unmapped label skipped -> 2 items with boxes
    assert [i["label"] for i in items] == ["samosa", "idli"]
    assert items[0]["box"] == [0, 0, 100, 100]
    assert items[1]["nutrition"]["kcal"]["min"] > 0


@pytest.mark.django_db
def test_scan_portion_scales_with_box_area(
    auth_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portion v1: the larger region gets more grams than the smaller one."""
    _seed_idli()

    def region(box: list[int], label: str) -> dict[str, Any]:
        return {"box": box, "score": 0.9, "predictions": [{"label": label, "confidence": 0.9}]}

    # big samosa region (200x200) vs small idli region (50x50)
    regions = [region([0, 0, 200, 200], "samosa"), region([0, 0, 50, 50], "idli")]
    monkeypatch.setattr(
        "scans.views.classify",
        _fake_classify([{"label": "samosa", "confidence": 0.9}], regions=regions),
    )
    resp = auth_client.post("/api/v1/scan/", {"image": _jpeg()}, format="multipart")
    grams = {i["label"]: i["portion"]["grams"] for i in resp.json()["items"]}
    assert grams["samosa"] > 100  # default samosa is 100 g -> scaled up (bigger box)
    assert grams["idli"] < 75  # default idli is 75 g -> scaled down (smaller box)


def _seed_idli() -> None:
    food = Food.objects.create(source="IFCT", source_id="idli1", name="Idli", food_group="cereal")
    amounts = {"energy_kcal": "128", "protein_g": "4", "carb_g": "26", "fat_g": "1"}
    for key, amount in amounts.items():
        nutrient, _ = Nutrient.objects.get_or_create(
            key_name=key, defaults={"display_name": key, "unit": "g"}
        )
        FoodNutrient.objects.create(food=food, nutrient=nutrient, amount_per_100g=amount)
    vision_class = VisionClass.objects.create(label="idli", food=food, match_quality="exact")
    PortionUnit.objects.create(vision_class=vision_class, unit="piece", grams="75", is_default=True)


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
