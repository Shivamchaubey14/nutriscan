"""Benchmark ONNX classifier CPU latency: fp32 vs INT8.

Writes inference/benchmark.json (mean/p95 ms per single-image inference) — the
numbers behind the SRS p95 target and a README chart later.

Run:  uv run python inference/benchmark.py [--runs 100]
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort  # type: ignore[import-untyped]

MODELS = Path(__file__).parent / "models"
TARGET_MS = 300.0


def bench(path: Path, runs: int, warmup: int) -> dict[str, float]:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    name = session.get_inputs()[0].name
    rng = np.random.default_rng(0)
    x = rng.standard_normal((1, 3, 384, 384), dtype=np.float32)

    for _ in range(warmup):
        session.run(None, {name: x})
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        session.run(None, {name: x})
        samples.append((time.perf_counter() - start) * 1000.0)

    arr = np.array(samples)
    return {
        "mean_ms": round(float(arr.mean()), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "size_kb": path.stat().st_size // 1024,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    report: dict[str, object] = {}
    for name, filename in [("fp32", "classifier_v1.onnx"), ("int8", "classifier_v1.int8.onnx")]:
        path = MODELS / filename
        if path.exists():
            report[name] = bench(path, args.runs, args.warmup)

    report["target_ms"] = TARGET_MS
    (MODELS.parent / "benchmark.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
