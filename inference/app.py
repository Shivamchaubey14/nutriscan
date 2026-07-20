"""FastAPI inference service: image in -> top-k food labels + confidences.

The ONNX model is loaded once at startup. Runtime is torch-free (onnxruntime +
PIL + numpy) so the container stays small.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from inference.model import Classifier, load_classifier
from inference.preprocess import preprocess

MODEL_VERSION = "baseline_v1"
_state: dict[str, Classifier] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _state["classifier"] = load_classifier()
    yield
    _state.clear()


app = FastAPI(title="NutriScan Inference", version="1.0.0", lifespan=lifespan)


class PredictionOut(BaseModel):
    label: str
    confidence: float


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[PredictionOut]


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "model_loaded": "classifier" in _state}


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
    return PredictResponse(
        model_version=MODEL_VERSION,
        predictions=[PredictionOut(label=p.label, confidence=p.confidence) for p in results],
    )
