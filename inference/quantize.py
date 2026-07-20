"""Dynamic INT8 quantization of the exported ONNX classifier.

Dynamic quantization needs no calibration data: weights are quantized to int8 at
export time and activations at run time. It shrinks the model ~4x and speeds up
CPU inference, which is what the service runs on. Benchmark the two with
inference/benchmark.py before choosing which to serve.

Run:  uv run python inference/quantize.py
"""

from pathlib import Path

from onnxruntime.quantization import (  # type: ignore[import-untyped]
    QuantType,
    quantize_dynamic,
)

MODELS = Path(__file__).parent / "models"


def main() -> None:
    src = MODELS / "classifier_v1.onnx"
    dst = MODELS / "classifier_v1.int8.onnx"
    if not src.exists():
        raise SystemExit(f"{src} not found — run export_onnx.py first")
    quantize_dynamic(src, dst, weight_type=QuantType.QInt8)
    print(
        f"quantized -> {dst.name} "
        f"({dst.stat().st_size // 1024} KB, was {src.stat().st_size // 1024} KB)"
    )


if __name__ == "__main__":
    main()
