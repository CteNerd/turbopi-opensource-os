#!/usr/bin/env python3
"""Unit tests for vision benchmark harness."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vision.benchmark import (  # noqa: E402
    MockDetector,
    build_markdown_summary,
    percentile,
    run_benchmark,
)


class TestBenchmarkHarness(unittest.TestCase):
    def test_percentile_linear_interpolation(self):
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertAlmostEqual(percentile([10.0], 0.95), 10.0)
        self.assertAlmostEqual(percentile([], 0.95), 0.0)

    def test_runs_multiple_models_and_resolutions(self):
        results = run_benchmark(
            detectors=[MockDetector("mobilenet_ssd_v2"), MockDetector("yolov5n_int8")],
            resolutions=[320, 416, 640],
            warmup_frames=3,
            measure_frames=12,
            max_cpu_temp_c=90.0,
        )

        self.assertEqual(len(results), 6)
        models = {result.model for result in results}
        self.assertEqual(models, {"mobilenet_ssd_v2", "yolov5n_int8"})

        for result in results:
            self.assertGreater(result.frames, 0)
            self.assertGreater(result.fps, 0.0)
            self.assertGreater(result.p95_latency_ms, result.p50_latency_ms)
            self.assertEqual(result.dropped_frames, 0)
            self.assertTrue(result.stability_ok)

    def test_markdown_summary_contains_expected_columns(self):
        results = run_benchmark(
            detectors=[MockDetector("yolov5n_int8")],
            resolutions=[320],
            warmup_frames=1,
            measure_frames=8,
            max_cpu_temp_c=90.0,
        )
        markdown = build_markdown_summary(results)

        self.assertIn("Model | Resolution | FPS | P50 (ms) | P95 (ms) | Max CPU Temp (C) | Stable", markdown)
        self.assertIn("yolov5n_int8", markdown)
        self.assertIn("320p", markdown)


if __name__ == "__main__":
    unittest.main()
