#!/usr/bin/env python3
"""Benchmark harness for vision model discovery.

This module provides a deterministic mock backend so model comparisons are
repeatable in CI and on developer machines without camera/model dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Protocol


@dataclass(frozen=True)
class BenchmarkResult:
    """Per-model, per-resolution benchmark metrics."""

    model: str
    resolution: int
    frames: int
    fps: float
    p50_latency_ms: float
    p95_latency_ms: float
    max_cpu_temp_c: float
    stability_ok: bool
    dropped_frames: int


class Detector(Protocol):
    """Protocol for benchmarkable detector backends."""

    def name(self) -> str:
        """Return stable model identifier."""

    def infer_latency_ms(self, resolution: int, frame_idx: int) -> float:
        """Return inference latency for one frame in milliseconds."""


class MockDetector:
    """Deterministic detector profile used for model discovery comparisons."""

    _BASE_LATENCY_320_MS: Dict[str, float] = {
        "mobilenet_ssd_v2": 15.5,
        "yolov5n_int8": 11.2,
        "efficientdet_lite0": 18.0,
    }

    def __init__(self, model_name: str):
        if model_name not in self._BASE_LATENCY_320_MS:
            raise ValueError(
                f"Unknown mock model '{model_name}'. "
                f"Available: {', '.join(sorted(self._BASE_LATENCY_320_MS))}"
            )
        self._model_name = model_name

    def name(self) -> str:
        return self._model_name

    def infer_latency_ms(self, resolution: int, frame_idx: int) -> float:
        base = self._BASE_LATENCY_320_MS[self._model_name]
        scale = math.pow(resolution / 320.0, 1.14)
        # Small deterministic jitter to approximate real run-to-run variance.
        jitter = ((frame_idx % 7) - 3) * 0.08
        return max(1.0, base * scale + jitter)


def percentile(values: List[float], p: float) -> float:
    """Return percentile with linear interpolation."""
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(sorted_values[int(index)])
    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    return lower_value + (upper_value - lower_value) * (index - lower)


def estimate_cpu_temp_c(model: str, resolution: int, p95_latency_ms: float) -> float:
    """Estimate thermal load for mock runs so metrics include temperature."""
    model_bias = {
        "mobilenet_ssd_v2": 1.0,
        "yolov5n_int8": 0.5,
        "efficientdet_lite0": 2.0,
    }.get(model, 1.5)
    resolution_bias = (resolution - 320) / 160.0
    latency_bias = p95_latency_ms / 25.0
    return round(49.0 + model_bias + resolution_bias + latency_bias, 1)


def run_benchmark(
    detectors: Iterable[Detector],
    resolutions: Iterable[int],
    warmup_frames: int,
    measure_frames: int,
    max_cpu_temp_c: float,
) -> List[BenchmarkResult]:
    """Run benchmark for all detector-resolution combinations."""
    results: List[BenchmarkResult] = []

    for detector in detectors:
        model_name = detector.name()
        for resolution in resolutions:
            for idx in range(warmup_frames):
                detector.infer_latency_ms(resolution, idx)

            latencies_ms: List[float] = []
            dropped = 0
            for idx in range(measure_frames):
                latency = detector.infer_latency_ms(resolution, idx)
                if latency <= 0:
                    dropped += 1
                    continue
                latencies_ms.append(latency)

            measured_frames = len(latencies_ms)
            total_latency_s = sum(latencies_ms) / 1000.0
            fps = measured_frames / total_latency_s if total_latency_s > 0 else 0.0
            p50 = percentile(latencies_ms, 0.50)
            p95 = percentile(latencies_ms, 0.95)
            max_temp = estimate_cpu_temp_c(model_name, resolution, p95)
            stable = (dropped == 0) and (max_temp <= max_cpu_temp_c)

            results.append(
                BenchmarkResult(
                    model=model_name,
                    resolution=resolution,
                    frames=measured_frames,
                    fps=round(fps, 2),
                    p50_latency_ms=round(p50, 2),
                    p95_latency_ms=round(p95, 2),
                    max_cpu_temp_c=max_temp,
                    stability_ok=stable,
                    dropped_frames=dropped,
                )
            )
    return results


def build_markdown_summary(results: List[BenchmarkResult]) -> str:
    """Build markdown table for docs and PR description usage."""
    header = (
        "Model | Resolution | FPS | P50 (ms) | P95 (ms) | Max CPU Temp (C) | "
        "Stable\n"
        "--- | ---: | ---: | ---: | ---: | ---: | ---"
    )
    rows = []
    for result in results:
        rows.append(
            "{model} | {resolution}p | {fps:.2f} | {p50:.2f} | {p95:.2f} | "
            "{temp:.1f} | {stable}".format(
                model=result.model,
                resolution=result.resolution,
                fps=result.fps,
                p50=result.p50_latency_ms,
                p95=result.p95_latency_ms,
                temp=result.max_cpu_temp_c,
                stable="yes" if result.stability_ok else "no",
            )
        )
    return "\n".join([header] + rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vision model benchmark harness")
    parser.add_argument(
        "--models",
        default="mobilenet_ssd_v2,yolov5n_int8",
        help="Comma-separated model profile names",
    )
    parser.add_argument(
        "--resolutions",
        default="320,416,640",
        help="Comma-separated input resolutions",
    )
    parser.add_argument("--warmup-frames", type=int, default=20)
    parser.add_argument("--measure-frames", type=int, default=180)
    parser.add_argument("--max-cpu-temp-c", type=float, default=78.0)
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path to write JSON results",
    )
    parser.add_argument(
        "--output-markdown",
        default="",
        help="Optional path to write markdown summary",
    )
    return parser.parse_args()


def _write_file(path: str, content: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_obj:
        file_obj.write(content)


def main() -> int:
    args = parse_args()
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    resolutions = [int(item.strip()) for item in args.resolutions.split(",") if item.strip()]

    detectors = [MockDetector(model_name) for model_name in models]
    results = run_benchmark(
        detectors=detectors,
        resolutions=resolutions,
        warmup_frames=args.warmup_frames,
        measure_frames=args.measure_frames,
        max_cpu_temp_c=args.max_cpu_temp_c,
    )

    json_blob = json.dumps([asdict(item) for item in results], indent=2)
    markdown = build_markdown_summary(results)

    if args.output_json:
        _write_file(args.output_json, json_blob + "\n")
    if args.output_markdown:
        _write_file(args.output_markdown, markdown + "\n")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
