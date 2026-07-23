"""Integration test for the multi-item /predict path with tiny fixture models."""

import io
import json
import os
from collections.abc import Iterator
from typing import cast

import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image
from torch import nn

CLASSES = ["dal", "idli", "rice"]
BOWL = 45
N_ANCHORS = 8400  # what the decode sees; content is constant


class _TinyClassifier(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.fc = nn.Linear(3, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = self.fc(x.mean(dim=(2, 3)))
        return out


class _TinyDetector(nn.Module):
    """Ignores pixels; always reports two confident, well-separated bowls."""

    def __init__(self) -> None:
        super().__init__()
        pred = torch.zeros(1, 84, N_ANCHORS)
        # Test image is 400x400 -> letterbox scale 1.6, no padding.
        # Bowl 1: letterbox (160,160) w/h 160 -> image (50,50)-(150,150)
        pred[0, :4, 0] = torch.tensor([160.0, 160.0, 160.0, 160.0])
        pred[0, 4 + BOWL, 0] = 0.9
        # Bowl 2: letterbox (480,480) w/h 160 -> image (250,250)-(350,350)
        pred[0, :4, 1] = torch.tensor([480.0, 480.0, 160.0, 160.0])
        pred[0, 4 + BOWL, 1] = 0.8
        self.register_buffer("pred", pred)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = cast(torch.Tensor, self.pred) + 0.0 * x.sum()
        return out


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    model_dir = tmp_path_factory.mktemp("models")

    classifier_path = model_dir / "classifier.onnx"
    torch.onnx.export(
        _TinyClassifier(len(CLASSES)).eval(),
        (torch.randn(1, 3, 384, 384),),
        str(classifier_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,
    )
    detector_path = model_dir / "detector.onnx"
    torch.onnx.export(
        _TinyDetector().eval(),
        (torch.randn(1, 3, 640, 640),),
        str(detector_path),
        input_names=["images"],
        output_names=["output"],
        dynamo=False,
    )
    classes_path = model_dir / "classes.json"
    classes_path.write_text(json.dumps(CLASSES), encoding="utf-8")

    os.environ["INFERENCE_MODEL_PATH"] = str(classifier_path)
    os.environ["INFERENCE_CLASSES_PATH"] = str(classes_path)
    os.environ["INFERENCE_DETECTOR_PATH"] = str(detector_path)
    from inference.app import app

    with TestClient(app) as test_client:
        yield test_client

    for key in ("INFERENCE_MODEL_PATH", "INFERENCE_CLASSES_PATH", "INFERENCE_DETECTOR_PATH"):
        os.environ.pop(key, None)


def _jpeg(size: int = 400) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), (180, 120, 60)).save(buf, "JPEG")
    return buf.getvalue()


def test_health_reports_detector(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["model_loaded"] is True
    assert body["detector_loaded"] is True


def test_predict_returns_regions(client: TestClient) -> None:
    resp = client.post("/predict", files={"image": ("thali.jpg", _jpeg(), "image/jpeg")})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["predictions"]) == 3  # whole-image path still present

    regions = body["regions"]
    assert len(regions) == 2
    assert regions[0]["score"] == pytest.approx(0.9, abs=1e-6)
    assert regions[0]["box"] == [50, 50, 150, 150]
    assert regions[1]["box"] == [250, 250, 350, 350]
    for region in regions:
        labels = [p["label"] for p in region["predictions"]]
        assert set(labels) <= set(CLASSES)
        confs = [p["confidence"] for p in region["predictions"]]
        assert confs == sorted(confs, reverse=True)
