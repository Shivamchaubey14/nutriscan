"""Seed the nutrition tables from the committed CSV seeds + mapping YAML.

Idempotent (upserts), so it is safe to re-run. Reads the same source files as the
standalone Day-4 loader: backend/db/seeds/*.csv and backend/db/nutrition_map.yaml.

    python manage.py seed_nutrition
"""

import csv
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from nutrition.models import Food, FoodNutrient, Nutrient, PortionUnit, VisionClass

DB_DIR = Path(settings.BASE_DIR) / "db"
NUTRIENTS = [
    ("energy_kcal", "Energy", "kcal"),
    ("protein_g", "Protein", "g"),
    ("fat_g", "Total fat", "g"),
    ("carb_g", "Carbohydrate", "g"),
    ("fiber_g", "Dietary fiber", "g"),
]


class Command(BaseCommand):
    help = "Load foods, nutrients and the vision-class mapping into the database."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        nutrients = {
            key: Nutrient.objects.update_or_create(
                key_name=key, defaults={"display_name": display, "unit": unit}
            )[0]
            for key, display, unit in NUTRIENTS
        }

        foods = self._load_foods("IFCT", "ifct_foods.csv") + self._load_foods(
            "USDA", "usda_foods.csv"
        )
        for row in foods:
            food, _ = Food.objects.update_or_create(
                source=row["source"],
                source_id=row["source_id"],
                defaults={"name": row["name"], "food_group": row["food_group"]},
            )
            for key in nutrients:
                if row.get(key):
                    FoodNutrient.objects.update_or_create(
                        food=food,
                        nutrient=nutrients[key],
                        defaults={"amount_per_100g": row[key]},
                    )

        mapping: dict[str, Any] = yaml.safe_load(
            (DB_DIR / "nutrition_map.yaml").read_text(encoding="utf-8")
        )["classes"]
        for label, spec in mapping.items():
            food = Food.objects.get(source=spec["source"], source_id=str(spec["source_id"]))
            vision_class, _ = VisionClass.objects.update_or_create(
                label=label,
                defaults={
                    "food": food,
                    "match_quality": spec["match"],
                    "note": spec.get("note", ""),
                },
            )
            for portion in spec["portions"]:
                PortionUnit.objects.update_or_create(
                    vision_class=vision_class,
                    unit=portion["unit"],
                    defaults={
                        "grams": portion["grams"],
                        "is_default": bool(portion.get("default")),
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"seeded {Food.objects.count()} foods, "
                f"{VisionClass.objects.count()} classes, "
                f"{PortionUnit.objects.count()} portions"
            )
        )

    def _load_foods(self, source: str, filename: str) -> list[dict[str, str]]:
        with open(DB_DIR / "seeds" / filename, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["source"] = source
        return rows
