"""Meal log — what the user actually ate, for daily calorie totals vs their goal."""

from django.conf import settings
from django.db import models


class MealLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_logs"
    )
    scan = models.ForeignKey(
        "scans.Scan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_logs",
    )
    label = models.CharField(max_length=64)
    kcal = models.PositiveIntegerField()
    portion_grams = models.DecimalField(max_digits=7, decimal_places=1)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self) -> str:
        return f"{self.label} — {self.kcal} kcal"
