"""Image preprocessing for the ONNX classifier — no torch at runtime.

Mirrors torchvision's EfficientNet_V2_S_Weights.IMAGENET1K_V1 transforms (resize
shorter side to 384, center-crop 384, scale to [0,1], ImageNet normalize) using
only PIL + numpy so the inference image stays small.
"""

import io

import numpy as np
from PIL import Image

SIZE = 384
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(data: bytes) -> np.ndarray:
    """Decode image bytes to a normalized (1, 3, 384, 384) float32 NCHW batch."""
    with Image.open(io.BytesIO(data)) as im:
        img = im.convert("RGB")
        w, h = img.size
        scale = SIZE / min(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.Resampling.BILINEAR)
        rw, rh = img.size
        left, top = (rw - SIZE) // 2, (rh - SIZE) // 2
        img = img.crop((left, top, left + SIZE, top + SIZE))
        arr = np.asarray(img, dtype=np.float32) / 255.0

    arr = (arr - MEAN) / STD
    arr = arr.transpose(2, 0, 1)  # HWC -> CHW
    return arr[np.newaxis, :].astype(np.float32)
