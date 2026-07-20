"""Async /scan endpoint: image -> inference service -> nutrition -> SRS §7 shape.

Non-blocking end to end: the inference call uses httpx.AsyncClient, and the ORM /
cache work is wrapped in sync_to_async so a slow model call never blocks the worker.
"""

import httpx
from accounts.models import User
from adrf.views import APIView as AsyncAPIView  # type: ignore[import-untyped]
from asgiref.sync import sync_to_async
from nutrition.resolver import resolve_nutrition
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from scans.inference_client import classify
from scans.models import Scan
from scans.serializers import FeedbackSerializer, ScanSerializer

# FR-3: below this confidence the app should ask the user to confirm the dish.
CONFIDENCE_THRESHOLD = 0.55


class ScanView(AsyncAPIView):  # type: ignore[misc]
    async def post(self, request: Request) -> Response:
        upload = request.FILES.get("image")
        if upload is None:
            return Response({"detail": "no image provided"}, status=400)

        image_bytes = upload.read()
        try:
            result = await classify(image_bytes, upload.name or "image.jpg")
        except httpx.HTTPError:
            return Response({"detail": "inference service unavailable"}, status=502)

        predictions = result.get("predictions", [])
        if not predictions:
            return Response({"detail": "no prediction"}, status=422)

        top = predictions[0]
        nutrition = await sync_to_async(resolve_nutrition)(top["label"])
        items = []
        if nutrition is not None:
            items.append(
                {"label": top["label"], "confidence": round(top["confidence"], 4), **nutrition}
            )

        model_version = result.get("model_version", "unknown")
        assert isinstance(request.user, User)  # guaranteed by IsAuthenticated
        scan = await Scan.objects.acreate(
            user=request.user,
            label=top["label"],
            confidence=top["confidence"],
            model_version=model_version,
        )

        return Response(
            {
                "scan_id": str(scan.id),
                "model_version": model_version,
                "needs_confirmation": top["confidence"] < CONFIDENCE_THRESHOLD,
                "items": items,
                "candidates": [
                    {"label": p["label"], "confidence": round(p["confidence"], 4)}
                    for p in predictions
                ],
            }
        )


class FeedbackView(APIView):
    """FR-15/16: confirm or correct a scan's label; corrections feed retraining."""

    def post(self, request: Request, scan_id: str) -> Response:
        scan = get_object_or_404(Scan, id=scan_id, user=request.user)
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan.confirmed = serializer.validated_data["confirmed"]
        scan.corrected_label = serializer.validated_data.get("corrected_label", "")
        scan.save(update_fields=["confirmed", "corrected_label"])
        return Response(ScanSerializer(scan).data)
