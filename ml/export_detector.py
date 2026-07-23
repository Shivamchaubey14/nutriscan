"""Export a stock COCO YOLOv8n to ONNX as the food-region detector.

No fine-tune (we have no box annotations for our labels): the COCO model only
proposes food-shaped regions — bowls/cups/pizza/fruit — and the 58-class
classifier names the dish inside each crop (see inference/detector.py).
ultralytics + torch are needed only here; the inference runtime stays torch-free.

Run:    uv run python ml/export_detector.py
Output: inference/models/detector_v1.onnx  (git-ignored, mounted at deploy)
"""

import shutil
from pathlib import Path

from ultralytics import YOLO  # type: ignore[attr-defined]

OUT = Path(__file__).parent.parent / "inference" / "models" / "detector_v1.onnx"


def main() -> None:
    model = YOLO("yolov8n.pt")  # downloads on first run (~6 MB)
    exported = model.export(format="onnx", imgsz=640, opset=17, simplify=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(exported), OUT)
    # The .pt lands in the CWD on download; keep the tree clean.
    Path("yolov8n.pt").unlink(missing_ok=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
