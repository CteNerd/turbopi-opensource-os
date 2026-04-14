#!/usr/bin/env python3
"""Unit tests for vision detection engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.camera import CameraCalibration, CameraFrame, FakeCameraHAL
from vision.detection import Detection, DetectionEngine, mock_person_detector


def _make_frame() -> CameraFrame:
    hal = FakeCameraHAL(calibration=CameraCalibration(width=320, height=240))
    hal.open()
    return hal.get_frame()


class TestDetection(unittest.TestCase):
    def test_properties(self):
        d = Detection(label="person", confidence=0.9, x1=0.2, y1=0.1, x2=0.8, y2=0.9)
        self.assertAlmostEqual(d.cx, 0.5)
        self.assertAlmostEqual(d.cy, 0.5)
        self.assertAlmostEqual(d.width, 0.6)
        self.assertAlmostEqual(d.height, 0.8)
        self.assertAlmostEqual(d.area, 0.48)


class TestDetectionEngine(unittest.TestCase):
    def setUp(self):
        self.frame = _make_frame()

    def test_runs_detector_on_every_frame_by_default(self):
        call_count = [0]

        def counting_detector(f):
            call_count[0] += 1
            return mock_person_detector(f)

        engine = DetectionEngine(detector_fn=counting_detector)
        for _ in range(5):
            engine.process_frame(self.frame)
        self.assertEqual(call_count[0], 5)

    def test_interval_frames_throttles_detection(self):
        call_count = [0]

        def counting_detector(f):
            call_count[0] += 1
            return mock_person_detector(f)

        engine = DetectionEngine(detector_fn=counting_detector, interval_frames=3)
        for _ in range(9):
            engine.process_frame(self.frame)
        self.assertEqual(call_count[0], 3)

    def test_cached_results_returned_between_intervals(self):
        engine = DetectionEngine(detector_fn=mock_person_detector, interval_frames=5)
        results_frame1 = engine.process_frame(self.frame)
        self.assertEqual(len(results_frame1), 1)
        # Frame 2–4 still return the cached result.
        for _ in range(3):
            cached = engine.process_frame(self.frame)
            self.assertEqual(len(cached), 1)

    def test_min_confidence_filters_low_confidence(self):
        def low_conf_detector(f):
            return [
                Detection(label="person", confidence=0.2, x1=0.1, y1=0.1, x2=0.5, y2=0.5)
            ]

        engine = DetectionEngine(detector_fn=low_conf_detector, min_confidence=0.5)
        results = engine.process_frame(self.frame)
        self.assertEqual(len(results), 0)

    def test_invalid_interval_raises(self):
        with self.assertRaises(ValueError):
            DetectionEngine(detector_fn=mock_person_detector, interval_frames=0)

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            DetectionEngine(detector_fn=mock_person_detector, min_confidence=1.5)


if __name__ == "__main__":
    unittest.main()
