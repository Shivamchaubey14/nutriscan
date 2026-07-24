"""Unit tests for the YOLO decode pipeline in inference/detector.py — no model file."""

import numpy as np
import pytest
from PIL import Image

from inference.detector import CONF_THRESHOLD, MAX_ITEMS, Region, decode, letterbox, nms

BOWL, PERSON = 45, 0  # COCO class ids
N_CLASSES = 80


def _raw_output(detections: list[tuple[float, float, float, float, int, float]]) -> np.ndarray:
    """Build a fake YOLOv8 head output (1, 4+80, N) from (cx, cy, w, h, cls, score) rows."""
    n = len(detections)
    pred = np.zeros((4 + N_CLASSES, n), dtype=np.float32)
    for j, (cx, cy, w, h, cls, score) in enumerate(detections):
        pred[:4, j] = (cx, cy, w, h)
        pred[4 + cls, j] = score
    return pred[np.newaxis]


def test_letterbox_pads_and_scales() -> None:
    batch, scale, pad_x, pad_y = letterbox(Image.new("RGB", (1280, 640)), size=640)
    assert batch.shape == (1, 3, 640, 640)
    assert scale == 0.5
    assert pad_x == 0 and pad_y == 160  # wide image -> vertical padding


def test_nms_suppresses_overlaps_keeps_distinct() -> None:
    boxes = np.array([[0, 0, 100, 100], [10, 10, 110, 110], [300, 300, 400, 400]], dtype=float)
    scores = np.array([0.9, 0.8, 0.7])
    kept = nms(boxes, scores, iou_threshold=0.45)
    assert kept == [0, 2]  # near-duplicate of the winner is dropped, distinct box kept


def test_decode_filters_classes_and_maps_back_to_image() -> None:
    # 800x400 image letterboxed into 640: scale 0.8, pad_y (640-320)//2 = 160.
    output = _raw_output(
        [
            (160.0, 240.0, 160.0, 160.0, BOWL, 0.9),  # bowl at image (100,100)-(300,200)...
            (480.0, 240.0, 100.0, 100.0, PERSON, 0.99),  # person: not a food region
            (480.0, 240.0, 100.0, 100.0, BOWL, 0.1),  # below confidence threshold
        ]
    )
    regions = decode(output, scale=0.8, pad_x=0, pad_y=160, img_w=800, img_h=400)
    assert len(regions) == 1
    (r,) = regions
    assert r.score == pytest.approx(0.9, abs=1e-6)
    # cx 160, w 160 -> letterbox x 80..240 -> /0.8 -> 100..300
    # cy 240, h 160 -> letterbox y 160..320 -> minus pad 160 -> 0..160 -> /0.8 -> 0..200
    assert r.box == (100, 0, 300, 200)


def test_decode_caps_items() -> None:
    rows = [
        (float(50 + 120 * i), 320.0, 80.0, 80.0, BOWL, CONF_THRESHOLD + 0.01 * i)
        for i in range(MAX_ITEMS + 3)
    ]
    regions = decode(_raw_output(rows), scale=1.0, pad_x=0, pad_y=0, img_w=1000, img_h=640)
    assert len(regions) == MAX_ITEMS
    # kept by score, best first
    scores = [r.score for r in regions]
    assert scores == sorted(scores, reverse=True)


def test_decode_empty_when_nothing_confident() -> None:
    output = _raw_output([(100.0, 100.0, 50.0, 50.0, BOWL, 0.05)])
    assert decode(output, scale=1.0, pad_x=0, pad_y=0, img_w=640, img_h=640) == []


def test_decode_drops_boxes_off_the_image() -> None:
    # A box centered far right of a narrow image collapses to zero width when
    # clipped — it must be dropped, not returned as a zero-area region.
    output = _raw_output([(900.0, 100.0, 40.0, 80.0, BOWL, 0.9)])
    assert decode(output, scale=1.0, pad_x=0, pad_y=0, img_w=100, img_h=640) == []


def test_region_is_plain_data() -> None:
    r = Region(box=(1, 2, 3, 4), score=0.5)
    assert r.box == (1, 2, 3, 4) and r.score == 0.5
