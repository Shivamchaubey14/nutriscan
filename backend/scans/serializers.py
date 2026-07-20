from typing import Any

from rest_framework import serializers

from scans.models import Scan


class ScanSerializer(serializers.ModelSerializer[Scan]):
    class Meta:
        model = Scan
        fields = (
            "id",
            "label",
            "confidence",
            "model_version",
            "created_at",
            "confirmed",
            "corrected_label",
        )
        read_only_fields = fields


class FeedbackSerializer(serializers.Serializer[Any]):
    confirmed = serializers.BooleanField()
    corrected_label = serializers.CharField(required=False, allow_blank=True, default="")
