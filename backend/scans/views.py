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

        # Resolve nutrition once per prediction; reused for both the top item and
        # the candidate list so a low-confidence correction already carries the
        # corrected dish's portion + calories (no second round trip on the phone).
        resolved = [(p, await sync_to_async(resolve_nutrition)(p["label"])) for p in predictions]

        top, top_nutrition = resolved[0]
        # FR-2 multi-item: when the detector found 2+ food regions, each region's
        # top prediction becomes an item. Dedupe by label (two katoris of the same
        # dal collapse to one adjustable portion) and skip unmapped labels.
        items = []
        seen_labels: set[str] = set()
        for region in result.get("regions", []):
            region_top = region["predictions"][0]
            label = region_top["label"]
            if label in seen_labels:
                continue
            nutrition = await sync_to_async(resolve_nutrition)(label)
            if nutrition is None:
                continue
            seen_labels.add(label)
            items.append(
                {
                    "label": label,
                    "confidence": round(region_top["confidence"], 4),
                    "box": region["box"],
                    **nutrition,
                }
            )
        if not items and top_nutrition is not None:
            items.append(
                {"label": top["label"], "confidence": round(top["confidence"], 4), **top_nutrition}
            )

        candidates = []
        for pred, nutrition in resolved:
            candidate = {"label": pred["label"], "confidence": round(pred["confidence"], 4)}
            if nutrition is not None:
                candidate.update(nutrition)
            candidates.append(candidate)

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
                "candidates": candidates,
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
