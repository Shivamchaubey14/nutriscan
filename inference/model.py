"""ONNX classifier wrapper: runs the session and returns top-k labelled results.

The model path and class list are resolved from the environment so the same code
serves the committed model or a test fixture:
  INFERENCE_MODEL_PATH   (default inference/models/classifier_v1.int8.onnx)
  INFERENCE_CLASSES_PATH (default inference/models/classes.json)
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]

MODELS_DIR = Path(__file__).parent / "models"


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = np.exp(logits - logits.max())
    result: np.ndarray = shifted / shifted.sum()
    return result


class Classifier:
    def __init__(self, model_path: Path, classes: list[str]) -> None:
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.classes = classes

    def predict(self, batch: np.ndarray, top_k: int = 3) -> list[Prediction]:
        logits = self.session.run(None, {self.input_name: batch})[0][0]
        probs = _softmax(logits)
        order = np.argsort(probs)[::-1][:top_k]
        return [Prediction(self.classes[i], float(probs[i])) for i in order]


def load_classifier() -> Classifier:
    # fp32 is the default: dynamic INT8 quantization measured ~18x slower on this
    # conv-heavy backbone (see inference/benchmark.json), so we serve fp32.
    model_path = Path(
        os.environ.get("INFERENCE_MODEL_PATH", str(MODELS_DIR / "classifier_v1.onnx"))
    )
    classes_path = Path(os.environ.get("INFERENCE_CLASSES_PATH", str(MODELS_DIR / "classes.json")))
    classes: list[str] = json.loads(classes_path.read_text(encoding="utf-8"))
    return Classifier(model_path, classes)
