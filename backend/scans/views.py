"""Async /scan endpoint: image -> inference service -> nutrition -> SRS §7 shape.

Non-blocking end to end: the inference call uses httpx.AsyncClient, and the ORM /
cache work is wrapped in sync_to_async so a slow model call never blocks the worker.
"""

import uuid

import httpx
from adrf.views import APIView  # type: ignore[import-untyped]
from asgiref.sync import sync_to_async
from nutrition.resolver import resolve_nutrition
from rest_framework.request import Request
from rest_framework.response import Response

from scans.inference_client import classify

# FR-3: below this confidence the app should ask the user to confirm the dish.
CONFIDENCE_THRESHOLD = 0.55


class ScanView(APIView):  # type: ignore[misc]
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

        return Response(
            {
                "scan_id": uuid.uuid4().hex[:8],
                "model_version": result.get("model_version", "unknown"),
                "needs_confirmation": top["confidence"] < CONFIDENCE_THRESHOLD,
                "items": items,
                "candidates": [
                    {"label": p["label"], "confidence": round(p["confidence"], 4)}
                    for p in predictions
                ],
            }
        )
