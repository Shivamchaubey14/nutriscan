"""Integration tests for the FastAPI inference service against a tiny ONNX model."""

import io
import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image
from torch import nn

CLASSES = ["apple", "banana", "idli"]


class _Tiny(nn.Module):
    """Global-average-pool then linear — same input/output contract as the real model."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.fc = nn.Linear(3, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = self.fc(x.mean(dim=(2, 3)))
        return out


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    model_dir = tmp_path_factory.mktemp("model")
    onnx_path = model_dir / "tiny.onnx"
    torch.onnx.export(
        _Tiny(len(CLASSES)).eval(),
        (torch.randn(1, 3, 384, 384),),
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,
    )
    classes_path = model_dir / "classes.json"
    classes_path.write_text(json.dumps(CLASSES), encoding="utf-8")

    os.environ["INFERENCE_MODEL_PATH"] = str(onnx_path)
    os.environ["INFERENCE_CLASSES_PATH"] = str(classes_path)
    from inference.app import app

    with TestClient(app) as test_client:
        yield test_client

    for key in ("INFERENCE_MODEL_PATH", "INFERENCE_CLASSES_PATH"):
        os.environ.pop(key, None)


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), (200, 140, 60)).save(buf, "JPEG")
    return buf.getvalue()


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "model_loaded": True}


def test_predict_returns_ranked_labels(client: TestClient) -> None:
    resp = client.post("/predict", files={"image": ("food.jpg", _jpeg(), "image/jpeg")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"] == "baseline_v1"
    preds = body["predictions"]
    assert len(preds) == 3
    assert {p["label"] for p in preds} <= set(CLASSES)
    confidences = [p["confidence"] for p in preds]
    assert confidences == sorted(confidences, reverse=True)
    assert sum(confidences) == pytest.approx(1.0, abs=1e-5)


def test_predict_top_k(client: TestClient) -> None:
    resp = client.post(
        "/predict", files={"image": ("food.jpg", _jpeg(), "image/jpeg")}, params={"top_k": 1}
    )
    assert resp.status_code == 200
    assert len(resp.json()["predictions"]) == 1


def test_predict_rejects_bad_image(client: TestClient) -> None:
    resp = client.post("/predict", files={"image": ("x.jpg", b"nope", "image/jpeg")})
    assert resp.status_code == 400


def test_export_module_shape() -> None:
    from inference.export_onnx import Classifier

    model = Classifier(num_classes=5).eval()
    with torch.no_grad():
        out = model(torch.randn(1, 3, 384, 384))
    assert out.shape == (1, 5)
    assert Path("inference/export_onnx.py").exists()
