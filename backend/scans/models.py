"""Scan records — one per POST /scan, so predictions can be reviewed, corrected
(FR-15/16, feeding retraining) and shown in history."""

import uuid

from django.conf import settings
from django.db import models


class Scan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scans"
    )
    label = models.CharField(max_length=64)
    confidence = models.FloatField()
    model_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    # Feedback: confirmed is None until the user responds, then True (correct)
    # or False (corrected_label holds what it should have been).
    confirmed = models.BooleanField(null=True, blank=True)
    corrected_label = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.label} ({self.confidence:.2f})"
