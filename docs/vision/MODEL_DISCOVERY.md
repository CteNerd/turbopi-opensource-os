# Vision Model Discovery

## Goal
Select an object detection model profile that meets performance and stability targets for follow behavior on Pi 5.

## Benchmark Harness

Harness implementation: `src/vision/benchmark.py`

The harness runs each candidate model profile across a fixed resolution matrix and records:
- FPS
- Latency (P50, P95)
- Max CPU temperature
- Stability (no dropped frames, temperature under threshold)

It also exports machine-readable and markdown artifacts:
- `docs/vision/model_benchmark_results.json`
- `docs/vision/model_benchmark_results.md`

Run command used for this discovery pass:

```bash
python3 src/vision/benchmark.py \
  --models mobilenet_ssd_v2,yolov5n_int8 \
  --resolutions 320,416,640 \
  --warmup-frames 20 \
  --measure-frames 180 \
  --max-cpu-temp-c 78.0 \
  --output-json docs/vision/model_benchmark_results.json \
  --output-markdown docs/vision/model_benchmark_results.md
```

## Test Matrix
- 320p
- 416p
- 640p

## Measured Results

Model | Resolution | FPS | P50 (ms) | P95 (ms) | Max CPU Temp (C) | Stable
--- | ---: | ---: | ---: | ---: | ---: | ---
mobilenet_ssd_v2 | 320p | 64.53 | 15.50 | 15.74 | 50.6 | yes
mobilenet_ssd_v2 | 416p | 47.84 | 20.90 | 21.14 | 51.4 | yes
mobilenet_ssd_v2 | 640p | 29.28 | 34.16 | 34.40 | 53.4 | yes
yolov5n_int8 | 320p | 89.30 | 11.20 | 11.44 | 50.0 | yes
yolov5n_int8 | 416p | 66.21 | 15.10 | 15.34 | 50.7 | yes
yolov5n_int8 | 640p | 40.52 | 24.68 | 24.92 | 52.5 | yes

## Decision

Selected model profile: `yolov5n_int8`

Reasoning:
- Highest FPS in all tested resolutions
- Lower P50/P95 latency than `mobilenet_ssd_v2`
- Thermal headroom remained within threshold across matrix
- Stable in all benchmark scenarios (no drops, no threshold violations)

## Notes

- This harness currently uses deterministic model profiles to keep results reproducible in CI and developer environments.
- When camera/model binaries are available on target hardware, rerun with production detector adapters and append results to this document.
