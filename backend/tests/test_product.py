"""FR-4 barcode path: Open Food Facts shaping + the /product/<barcode>/ endpoint."""

from typing import Any

import httpx
import pytest
from django.contrib.auth import get_user_model
from nutrition.off import _shape
from nutrition.resolver import scale_portion
from rest_framework.test import APIClient


def test_scale_portion_scales_grams_and_macros() -> None:
    block = {
        "portion": {"unit": "katori", "grams": 150, "adjustable": True},
        "nutrition": {
            "kcal": {"min": 200, "max": 280},
            "protein_g": 6.0,
            "carbs_g": 30.0,
            "fat_g": 4.0,
            "source": "IFCT",
        },
    }
    scaled = scale_portion(block, 1.5)
    assert scaled["portion"]["grams"] == 225
    assert scaled["nutrition"]["kcal"] == {"min": 300, "max": 420}
    assert scaled["nutrition"]["protein_g"] == 9.0
    assert scaled["nutrition"]["source"] == "IFCT"  # non-scaled fields preserved


OFF_PRODUCT = {
    "product_name": "Chocos",
    "brands": "Kellogg's",
    "serving_size": "30 g",
    "serving_quantity": 30,
    "nutriments": {
        "energy-kcal_100g": 400,
        "proteins_100g": 7,
        "carbohydrates_100g": 84,
        "fat_100g": 4,
    },
}


def test_shape_scales_to_serving() -> None:
    block = _shape("123", OFF_PRODUCT)
    assert block is not None
    assert block["name"] == "Kellogg's — Chocos"
    assert block["portion"] == {"unit": "30 g", "grams": 30, "adjustable": True}
    # 400 kcal/100g * 0.3 = 120, ±5%
    assert block["nutrition"]["kcal"] == {"min": 114, "max": 126}
    assert block["nutrition"]["carbs_g"] == pytest.approx(25.2)
    assert block["nutrition"]["source"] == "OFF"


def test_shape_defaults_to_100g_without_serving() -> None:
    product = {**OFF_PRODUCT}
    del product["serving_quantity"]
    del product["serving_size"]
    block = _shape("123", product)
    assert block is not None
    assert block["portion"]["unit"] == "100 g"
    assert block["portion"]["grams"] == 100


def test_shape_none_without_energy() -> None:
    assert _shape("123", {"product_name": "Mystery", "nutriments": {}}) is None


@pytest.fixture
def auth_client() -> APIClient:
    user = get_user_model().objects.create_user(email="shopper@example.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _mock_off(monkeypatch: pytest.MonkeyPatch, *, status: int, body: dict[str, Any]) -> None:
    class _Resp:
        status_code = status

        def json(self) -> dict[str, Any]:
            return body

    class _Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def get(self, *args: Any, **kwargs: Any) -> _Resp:
            return _Resp()

    monkeypatch.setattr("nutrition.off.httpx.AsyncClient", _Client)


@pytest.mark.django_db
def test_product_lookup_ok(auth_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_off(monkeypatch, status=200, body={"status": 1, "product": OFF_PRODUCT})
    resp = auth_client.get("/api/v1/product/5053827207003/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["barcode"] == "5053827207003"
    assert body["nutrition"]["source"] == "OFF"


@pytest.mark.django_db
def test_product_not_found(auth_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_off(monkeypatch, status=200, body={"status": 0})
    assert auth_client.get("/api/v1/product/0000/").status_code == 404


@pytest.mark.django_db
def test_product_upstream_error(auth_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom(*args: Any, **kwargs: Any) -> None:
        raise httpx.ConnectError("off down")

    # Make the AsyncClient.get raise a transport error.
    class _Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        get = _boom

    monkeypatch.setattr("nutrition.off.httpx.AsyncClient", _Client)
    assert auth_client.get("/api/v1/product/123/").status_code == 502


@pytest.mark.django_db
def test_product_requires_auth() -> None:
    assert APIClient().get("/api/v1/product/123/").status_code == 401
