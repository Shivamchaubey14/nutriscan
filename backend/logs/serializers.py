from rest_framework import serializers

from logs.models import MealLog


class MealLogSerializer(serializers.ModelSerializer[MealLog]):
    class Meta:
        model = MealLog
        fields = (
            "id",
            "label",
            "kcal",
            "portion_grams",
            "protein_g",
            "carbs_g",
            "fat_g",
            "scan",
            "logged_at",
        )
        read_only_fields = ("id", "logged_at")
