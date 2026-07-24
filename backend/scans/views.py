"""Async /scan endpoint: image -> inference service -> nutrition -> SRS §7 shape.

Non-blocking end to end: the inference call uses httpx.AsyncClient, and the ORM /
cache work is wrapped in sync_to_async so a slow model call never blocks the worker.
"""

from typing import Any

import httpx
from accounts.models import User
from adrf.views import APIView as AsyncAPIView  # type: ignore[import-untyped]
from asgiref.sync import sync_to_async
from nutrition.off import lookup_product
from nutrition.resolver import resolve_nutrition, scale_portion
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from scans.inference_client import classify
from scans.models import Scan
from scans.serializers import FeedbackSerializer, ScanSerializer

# FR-3: below this confidence the app should ask the user to confirm the dish.
CONFIDENCE_THRESHOLD = 0.55
# Portion-estimation v1: clamp the box-area factor so one huge/tiny region can't
# push the starting portion to an absurd grammage (it stays user-adjustable).
AREA_FACTOR_MIN, AREA_FACTOR_MAX = 0.7, 1.5


def _box_area(box: list[int]) -> float:
    return max(1.0, (box[2] - box[0]) * (box[3] - box[1]))


def _mean_box_area(regions: list[dict[str, Any]]) -> float:
    areas = [_box_area(r["box"]) for r in regions if r.get("box")]
    return sum(areas) / len(areas) if areas else 1.0


def _area_factor(box: list[int], mean_area: float) -> float:
    # sqrt so a 4x-area region ≈ 2x grams, not 4x; then clamp.
    factor: float = (_box_area(box) / mean_area) ** 0.5
    return min(AREA_FACTOR_MAX, max(AREA_FACTOR_MIN, factor))


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
        regions = result.get("regions", [])
        mean_area = _mean_box_area(regions)
        for region in regions:
            # Defensive against a malformed region shape (inference/backend version
            # skew): a bad region is skipped, not a 500 for the whole scan.
            predictions = region.get("predictions") or []
            if not predictions:
                continue
            label = predictions[0].get("label")
            if not label or label in seen_labels:
                continue
            block = await sync_to_async(resolve_nutrition)(label)
            if block is None:
                continue
            seen_labels.add(label)
            box = region.get("box")
            if box is not None:
                block = scale_portion(block, _area_factor(box, mean_area))
            item = {
                "label": label,
                "confidence": round(predictions[0].get("confidence", 0.0), 4),
                **block,
            }
            if box is not None:
                item["box"] = box
            items.append(item)
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


class ProductLookupView(AsyncAPIView):  # type: ignore[misc]
    """FR-4 barcode path: barcode -> Open Food Facts -> nutrition block."""

    async def get(self, request: Request, barcode: str) -> Response:
        try:
            product = await lookup_product(barcode)
        except httpx.HTTPError:
            return Response({"detail": "product lookup unavailable"}, status=502)
        if product is None:
            return Response({"detail": "product not found"}, status=404)
        return Response(product)


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
