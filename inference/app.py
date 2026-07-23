"""FastAPI inference service: image in -> top-k food labels + confidences.

Models load once at startup. Runtime is torch-free (onnxruntime + PIL + numpy)
so the container stays small. If the detector model is present, images with two
or more detected food regions also return per-region classifications (`regions`)
so the backend can build a multi-item scan; otherwise the service behaves
exactly as the single-item classifier.
"""

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from inference.detector import Detector, load_detector
from inference.model import Classifier, load_classifier
from inference.preprocess import preprocess, preprocess_image

MODEL_VERSION = "baseline_v1"
# Pad detector crops slightly — food often overflows the bowl rim.
CROP_PAD = 0.08
_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _state["classifier"] = load_classifier()
    _state["detector"] = load_detector()  # None -> single-item mode
    yield
    _state.clear()


app = FastAPI(title="NutriScan Inference", version="1.0.0", lifespan=lifespan)


class PredictionOut(BaseModel):
    label: str
    confidence: float


class RegionOut(BaseModel):
    box: list[int]  # x1, y1, x2, y2 in original-image pixels
    score: float  # detector confidence for the region
    predictions: list[PredictionOut]


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[PredictionOut]
    regions: list[RegionOut] = []


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": _state.get("classifier") is not None,
        "detector_loaded": _state.get("detector") is not None,
    }


def _padded_crop(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x1, y1, x2, y2 = box
    pad_w, pad_h = (x2 - x1) * CROP_PAD, (y2 - y1) * CROP_PAD
    return img.crop(
        (
            max(0, round(x1 - pad_w)),
            max(0, round(y1 - pad_h)),
            min(img.size[0], round(x2 + pad_w)),
            min(img.size[1], round(y2 + pad_h)),
        )
    )


def _detect_regions(
    classifier: Classifier, detector: Detector | None, data: bytes, top_k: int
) -> list[RegionOut]:
    """Classify each detected food region; [] unless 2+ regions (single-item scan)."""
    if detector is None:
        return []
    with Image.open(io.BytesIO(data)) as im:
        img = im.convert("RGB")
        found = detector.detect(img)
        if len(found) < 2:
            return []
        return [
            RegionOut(
                box=list(region.box),
                score=region.score,
                predictions=[
                    PredictionOut(label=p.label, confidence=p.confidence)
                    for p in classifier.predict(
                        preprocess_image(_padded_crop(img, region.box)), top_k=top_k
                    )
                ],
            )
            for region in found
        ]


@app.post("/predict", response_model=PredictResponse)
async def predict(image: UploadFile = File(...), top_k: int = 3) -> PredictResponse:
    classifier = _state.get("classifier")
    if classifier is None:  # pragma: no cover - startup guarantees this
        raise HTTPException(status_code=503, detail="model not loaded")
    data = await image.read()
    try:
        batch = preprocess(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid image") from exc
    results = classifier.predict(batch, top_k=top_k)
    regions = _detect_regions(classifier, _state.get("detector"), data, top_k)
    return PredictResponse(
        model_version=MODEL_VERSION,
        predictions=[PredictionOut(label=p.label, confidence=p.confidence) for p in results],
        regions=regions,
    )
