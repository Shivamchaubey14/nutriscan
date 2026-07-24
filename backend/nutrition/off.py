"""Open Food Facts lookup for packaged products (FR-4 barcode path).

Given a barcode, fetch the product from OFF and shape its per-100 g nutriments
into the same block the vision path returns (portion + kcal range + macros), so
the app renders a packaged scan exactly like a recognised dish. Async (httpx) to
keep /scan-style endpoints non-blocking.
"""

from typing import Any

import httpx
from django.conf import settings

# Packaged labels are precise, but declared values carry a tolerance and serving
# sizes vary — a small band keeps the "always a range" contract without faking it.
UNCERTAINTY = 0.05
FIELDS = "product_name,brands,nutriments,serving_size,serving_quantity"


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _shape(barcode: str, product: dict[str, Any]) -> dict[str, Any] | None:
    nutriments = product.get("nutriments", {})
    kcal_100g = _num(nutriments.get("energy-kcal_100g"))
    if kcal_100g is None:  # no usable energy value → treat as "not found"
        return None

    serving_g = _num(product.get("serving_quantity"))
    grams = serving_g if serving_g else 100.0
    unit = (product.get("serving_size") or f"{grams:g} g serving") if serving_g else "100 g"
    scale = grams / 100.0
    kcal = kcal_100g * scale

    def macro(key: str) -> float:
        value = _num(nutriments.get(key))
        return round(value * scale, 1) if value is not None else 0.0

    name = product.get("product_name") or "Unknown product"
    brands = product.get("brands")
    return {
        "barcode": barcode,
        "name": f"{brands} — {name}" if brands else name,
        "portion": {"unit": unit, "grams": round(grams, 1), "adjustable": True},
        "nutrition": {
            "kcal": {
                "min": round(kcal * (1 - UNCERTAINTY)),
                "max": round(kcal * (1 + UNCERTAINTY)),
            },
            "protein_g": macro("proteins_100g"),
            "carbs_g": macro("carbohydrates_100g"),
            "fat_g": macro("fat_100g"),
            "source": "OFF",
        },
    }


async def lookup_product(barcode: str) -> dict[str, Any] | None:
    """Return the shaped product block, or None if unknown / lacks nutrition."""
    url = f"{settings.OFF_BASE_URL.rstrip('/')}/api/v2/product/{barcode}.json"
    async with httpx.AsyncClient(
        timeout=settings.OFF_TIMEOUT, headers={"User-Agent": settings.OFF_USER_AGENT}
    ) as client:
        response = await client.get(url, params={"fields": FIELDS})
    if response.status_code != 200:
        return None
    body: dict[str, Any] = response.json()
    if body.get("status") != 1:
        return None
    return _shape(barcode, body.get("product", {}))
