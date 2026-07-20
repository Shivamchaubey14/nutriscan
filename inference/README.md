# Inference service

FastAPI microservice that turns a food photo into ranked labels + confidences.
The runtime is **torch-free** — onnxruntime + PIL + numpy — so the image stays
small. The heavy torch/onnx tooling is only used offline to produce the model.

## Endpoints

| Method | Path       | Purpose                                             |
|--------|------------|-----------------------------------------------------|
| GET    | `/health`  | Liveness + whether the model is loaded              |
| POST   | `/predict` | `multipart/form-data` image → top-k labels + scores |

```bash
curl -s -X POST http://localhost:8001/predict -F "image=@plate.jpg"
# {"model_version":"baseline_v1","predictions":[{"label":"pizza","confidence":0.90}, ...]}
```

## Producing the model (offline)

The ONNX weights are git-ignored (~77 MB). Regenerate them from the baseline
checkpoint (`ml/models/baseline_v1.pt`):

```bash
uv run python inference/export_onnx.py    # -> inference/models/classifier_v1.onnx (+ classes.json)
uv run python inference/quantize.py       # -> classifier_v1.int8.onnx (INT8)
uv run python inference/benchmark.py      # -> inference/benchmark.json
```

## Latency & the fp32 vs INT8 decision

Measured on CPU, single 384×384 image (`inference/benchmark.json`):

| model | mean     | p95      | size  |
|-------|----------|----------|-------|
| fp32  | ~128 ms  | ~150 ms  | 77 MB |
| INT8  | ~2310 ms | ~3750 ms | 20 MB |

Dynamic INT8 quantization made this **conv-heavy EfficientNetV2 backbone ~18×
slower** — onnxruntime lacks fast int8 convolution kernels on this CPU, so the
QDQ overhead dominates. fp32 already clears the 300 ms target, so **the service
serves fp32**; the INT8 path stays for reference and for hardware with VNNI/int8
conv support. Override the choice with `INFERENCE_MODEL_PATH`.

## Run

```bash
docker compose up --build inference   # http://localhost:8001
```
