"""Nutrition tables: foods, their per-100g nutrients, and the vision-class mapping.

Mirrors backend/db/schema.sql but owned by the ORM so the /scan resolver can use
Django queries. Seeded from backend/db/seeds + nutrition_map.yaml by the
seed_nutrition management command.
"""

from django.db import models


class Food(models.Model):
    class Source(models.TextChoices):
        IFCT = "IFCT"
        USDA = "USDA"

    source = models.CharField(max_length=4, choices=Source.choices)
    source_id = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    food_group = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "source_id"], name="uq_food_source")
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"


class Nutrient(models.Model):
    key_name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64)
    unit = models.CharField(max_length=8)

    def __str__(self) -> str:
        return self.key_name


class FoodNutrient(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="nutrients")
    nutrient = models.ForeignKey(Nutrient, on_delete=models.PROTECT)
    amount_per_100g = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["food", "nutrient"], name="uq_food_nutrient")
        ]


class VisionClass(models.Model):
    class Match(models.TextChoices):
        EXACT = "exact"
        PROXY = "proxy"

    label = models.CharField(max_length=64, unique=True)
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name="vision_classes")
    match_quality = models.CharField(max_length=8, choices=Match.choices, default=Match.EXACT)
    note = models.CharField(max_length=255, blank=True, default="")

    def __str__(self) -> str:
        return self.label


class PortionUnit(models.Model):
    vision_class = models.ForeignKey(VisionClass, on_delete=models.CASCADE, related_name="portions")
    unit = models.CharField(max_length=32)
    grams = models.DecimalField(max_digits=7, decimal_places=1)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["vision_class", "unit"], name="uq_portion")]

    def __str__(self) -> str:
        return f"{self.vision_class.label}: {self.unit} ({self.grams} g)"
