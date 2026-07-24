"""Resolve a predicted label to its default-portion nutrition (SRS §7 shape).

Single-image calorie estimation has irreducible error (hidden oil, sauces,
density), so calories are always returned as a range, never a point — SRS's
"no fake precision" principle. The per-class result is static, so it is cached.
"""

from typing import Any

from django.core.cache import cache

from nutrition.models import VisionClass

# ±band around the point estimate to express portion/preparation uncertainty.
UNCERTAINTY = 0.18
CACHE_TTL = 60 * 60 * 24


def _grams(value: float) -> float | int:
    return int(value) if value.is_integer() else round(value, 1)


def scale_portion(block: dict[str, Any], factor: float) -> dict[str, Any]:
    """Rescale a portion + nutrition block by `factor` (calories scale with grams).

    Portion-estimation v1: on a multi-item plate a bigger region gets more grams.
    The starting portion is only a hint — it stays user-adjustable via the slider.
    """
    portion, nutrition = block["portion"], block["nutrition"]
    return {
        **block,
        "portion": {**portion, "grams": _grams(float(portion["grams"]) * factor)},
        "nutrition": {
            **nutrition,
            "kcal": {
                "min": round(nutrition["kcal"]["min"] * factor),
                "max": round(nutrition["kcal"]["max"] * factor),
            },
            "protein_g": round(nutrition["protein_g"] * factor, 1),
            "carbs_g": round(nutrition["carbs_g"] * factor, 1),
            "fat_g": round(nutrition["fat_g"] * factor, 1),
        },
    }


def resolve_nutrition(label: str) -> dict[str, Any] | None:
    """Return the portion + nutrition block for a label, or None if unmapped."""
    cache_key = f"nutrition:{label}"
    cached: dict[str, Any] | None = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        vision_class = VisionClass.objects.select_related("food").get(label=label)
    except VisionClass.DoesNotExist:
        return None

    portion = vision_class.portions.filter(is_default=True).first()
    if portion is None:
        portion = vision_class.portions.first()
    if portion is None:
        return None

    per_100g = {
        fn.nutrient.key_name: float(fn.amount_per_100g)
        for fn in vision_class.food.nutrients.select_related("nutrient")
    }
    scale = float(portion.grams) / 100.0
    kcal = per_100g.get("energy_kcal", 0.0) * scale

    result: dict[str, Any] = {
        "portion": {
            "unit": portion.unit,
            "grams": _grams(float(portion.grams)),
            "adjustable": True,
        },
        "nutrition": {
            "kcal": {
                "min": round(kcal * (1 - UNCERTAINTY)),
                "max": round(kcal * (1 + UNCERTAINTY)),
            },
            "protein_g": round(per_100g.get("protein_g", 0.0) * scale, 1),
            "carbs_g": round(per_100g.get("carb_g", 0.0) * scale, 1),
            "fat_g": round(per_100g.get("fat_g", 0.0) * scale, 1),
            "source": vision_class.food.source,
        },
    }
    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result
