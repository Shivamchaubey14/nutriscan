"""Food-region detector: COCO-pretrained YOLOv8 ONNX as a region proposer.

We have no bounding-box annotations for our 58 classes, so v1 does not fine-tune
a detector. Instead a stock COCO model proposes food-shaped regions (bowls,
cups, pizza, fruit, ...) — on a thali each katori is its own "bowl" — and the
58-class classifier identifies the dish inside each crop. Torch-free at runtime
(onnxruntime + numpy), same as the classifier.

Env:
  INFERENCE_DETECTOR_PATH (default inference/models/detector_v1.onnx;
                           service runs single-item if the file is absent)
"""

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]
from PIL import Image

MODELS_DIR = Path(__file__).parent / "models"
INPUT_SIZE = 640
CONF_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45
# SRS risk table: v1 supports at most 4 items per frame.
MAX_ITEMS = 4
# COCO ids that plausibly contain one food item (containers + COCO's own foods).
FOOD_REGION_CLASS_IDS = frozenset({41, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55})
# 41 cup · 45 bowl · 46 banana · 47 apple · 48 sandwich · 49 orange ·
# 50 broccoli · 51 carrot · 52 hot dog · 53 pizza · 54 donut · 55 cake


@dataclass(frozen=True)
class Region:
    """A proposed food region in original-image pixel coordinates."""

    box: tuple[int, int, int, int]  # x1, y1, x2, y2
    score: float


def letterbox(img: Image.Image, size: int = INPUT_SIZE) -> tuple[np.ndarray, float, int, int]:
    """Resize keeping aspect, pad to size×size. Returns (batch, scale, pad_x, pad_y)."""
    w, h = img.size
    scale = size / max(w, h)
    new_w, new_h = round(w * scale), round(h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    pad_x, pad_y = (size - new_w) // 2, (size - new_h) // 2
    canvas.paste(resized, (pad_x, pad_y))
    arr = np.asarray(canvas, dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)[np.newaxis, :], scale, pad_x, pad_y


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = IOU_THRESHOLD) -> list[int]:
    """Greedy non-max suppression; returns kept indices, best score first."""
    order = np.argsort(scores)[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        x1 = np.maximum(boxes[i, 0], boxes[rest, 0])
        y1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        x2 = np.minimum(boxes[i, 2], boxes[rest, 2])
        y2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-9)
        order = rest[iou <= iou_threshold]
    return keep


def decode(
    output: np.ndarray,
    scale: float,
    pad_x: int,
    pad_y: int,
    img_w: int,
    img_h: int,
    conf_threshold: float = CONF_THRESHOLD,
) -> list[Region]:
    """Decode a YOLOv8 head output (1, 4+n_classes, n_anchors) into food regions."""
    pred = output[0]  # (4+C, N)
    boxes_xywh = pred[:4].T  # (N, 4) center-x, center-y, w, h in letterbox pixels
    class_scores = pred[4:].T  # (N, C)

    class_ids = class_scores.argmax(axis=1)
    scores = class_scores[np.arange(len(class_ids)), class_ids]
    food_mask = (scores >= conf_threshold) & np.isin(class_ids, list(FOOD_REGION_CLASS_IDS))
    if not food_mask.any():
        return []
    boxes_xywh, scores = boxes_xywh[food_mask], scores[food_mask]

    # xywh (letterbox) -> xyxy (original image)
    cx, cy, w, h = boxes_xywh.T
    boxes = np.stack(
        [
            (cx - w / 2 - pad_x) / scale,
            (cy - h / 2 - pad_y) / scale,
            (cx + w / 2 - pad_x) / scale,
            (cy + h / 2 - pad_y) / scale,
        ],
        axis=1,
    )
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, img_w)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, img_h)

    kept = nms(boxes, scores)[:MAX_ITEMS]
    return [
        Region(
            box=(int(boxes[i, 0]), int(boxes[i, 1]), int(boxes[i, 2]), int(boxes[i, 3])),
            score=float(scores[i]),
        )
        for i in kept
    ]


class Detector:
    def __init__(self, model_path: Path) -> None:
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def detect(self, img: Image.Image) -> list[Region]:
        batch, scale, pad_x, pad_y = letterbox(img)
        output = self.session.run(None, {self.input_name: batch})[0]
        return decode(output, scale, pad_x, pad_y, img_w=img.size[0], img_h=img.size[1])


def load_detector() -> "Detector | None":
    """Load the detector if its model file exists; None keeps single-item mode."""
    path = Path(os.environ.get("INFERENCE_DETECTOR_PATH", str(MODELS_DIR / "detector_v1.onnx")))
    if not path.exists():
        return None
    return Detector(path)
