"""Tests for the torch-free inference preprocessing."""

import io

import numpy as np
from PIL import Image

from inference.preprocess import SIZE, preprocess


def _jpeg(w: int, h: int, color: tuple[int, int, int] = (120, 60, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG")
    return buf.getvalue()


def test_output_shape_and_dtype() -> None:
    out = preprocess(_jpeg(640, 480))
    assert out.shape == (1, 3, SIZE, SIZE)
    assert out.dtype == np.float32


def test_handles_non_square_and_normalizes() -> None:
    out = preprocess(_jpeg(300, 900))
    # ImageNet-normalized values land in a small range around zero, not [0, 1].
    assert -3.0 < float(out.min()) < 3.0
    assert -3.0 < float(out.max()) < 3.0


def test_rejects_garbage_bytes() -> None:
    try:
        preprocess(b"not an image")
    except Exception:
        return
    raise AssertionError("expected preprocess to reject non-image bytes")
