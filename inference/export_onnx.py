"""Export the baseline classifier to ONNX.

Day-6 training saved only the linear head (ml/models/baseline_v1.pt) on top of a
frozen ImageNet EfficientNetV2-S backbone. This reassembles the two into one
module and exports it as a single ONNX graph the inference service can run
without torch. Classes are written alongside so the service can label outputs.

Run:  uv run python inference/export_onnx.py
"""

import json
from pathlib import Path
from typing import cast

import torch
from torch import nn
from torchvision.models import (  # type: ignore[import-untyped]
    EfficientNet_V2_S_Weights,
    efficientnet_v2_s,
)

ROOT = Path(__file__).parent.parent
CHECKPOINT = ROOT / "ml" / "models" / "baseline_v1.pt"
OUT_DIR = ROOT / "inference" / "models"
WEIGHTS = EfficientNet_V2_S_Weights.IMAGENET1K_V1
FEATURE_DIM = 1280
INPUT_SIZE = 384


class Classifier(nn.Module):
    """Frozen EfficientNetV2-S backbone followed by the trained linear head."""

    def __init__(self, num_classes: int) -> None:
        super().__init__()
        backbone = efficientnet_v2_s(weights=WEIGHTS)
        backbone.classifier = nn.Identity()
        self.backbone = backbone
        self.head = nn.Linear(FEATURE_DIM, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.head(self.backbone(x)))


def main() -> None:
    checkpoint = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
    classes: list[str] = checkpoint["classes"]

    model = Classifier(len(classes))
    model.head.load_state_dict(checkpoint["head"])
    model.eval()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = OUT_DIR / "classifier_v1.onnx"
    dummy = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)
    torch.onnx.export(
        model,
        (dummy,),
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )
    (OUT_DIR / "classes.json").write_text(json.dumps(classes, indent=2) + "\n", encoding="utf-8")
    print(f"exported {onnx_path} ({onnx_path.stat().st_size // 1024} KB), {len(classes)} classes")


if __name__ == "__main__":
    main()
