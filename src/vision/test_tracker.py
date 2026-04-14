#!/usr/bin/env python3
"""Unit tests for the IoU-based vision tracker."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vision.detection import Detection
from vision.tracker import Tracker, _iou


def _det(x1=0.1, y1=0.1, x2=0.5, y2=0.5, label="person", confidence=0.9) -> Detection:
    return Detection(label=label, confidence=confidence, x1=x1, y1=y1, x2=x2, y2=y2)


class TestIou(unittest.TestCase):
    def test_perfect_overlap(self):
        d = _det()
        self.assertAlmostEqual(_iou(d, d), 1.0)

    def test_no_overlap(self):
        a = _det(x1=0.0, y1=0.0, x2=0.2, y2=0.2)
        b = _det(x1=0.5, y1=0.5, x2=0.9, y2=0.9)
        self.assertAlmostEqual(_iou(a, b), 0.0)

    def test_partial_overlap(self):
        a = _det(x1=0.0, y1=0.0, x2=0.5, y2=0.5)
        b = _det(x1=0.25, y1=0.25, x2=0.75, y2=0.75)
        iou = _iou(a, b)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)


class TestTracker(unittest.TestCase):
    def test_new_detection_creates_track(self):
        tracker = Tracker()
        tracks = tracker.update([_det()])
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].track_id, 1)
        self.assertEqual(tracks[0].age, 1)

    def test_same_detection_increments_age(self):
        tracker = Tracker()
        tracker.update([_det()])
        tracks = tracker.update([_det()])
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].age, 2)
        self.assertEqual(tracks[0].track_id, 1)

    def test_separate_detections_get_separate_ids(self):
        tracker = Tracker()
        a = _det(x1=0.0, y1=0.0, x2=0.2, y2=0.2)
        b = _det(x1=0.6, y1=0.6, x2=0.9, y2=0.9)
        tracks = tracker.update([a, b])
        ids = {t.track_id for t in tracks}
        self.assertEqual(len(ids), 2)

    def test_missing_track_evicted_after_max_missed(self):
        tracker = Tracker(max_missed=2)
        tracker.update([_det()])
        # Stop providing this detection — track should be evicted after 2 missed.
        tracker.update([])
        tracker.update([])
        tracker.update([])
        self.assertEqual(len(tracker.all_tracks), 0)

    def test_track_not_evicted_before_max_missed(self):
        tracker = Tracker(max_missed=3)
        tracker.update([_det()])
        # Miss 2 frames (below threshold of 3).
        tracker.update([])
        tracker.update([])
        self.assertEqual(len(tracker.all_tracks), 1)

    def test_track_evicted_at_max_missed_boundary(self):
        tracker = Tracker(max_missed=2)
        tracker.update([_det()])
        tracker.update([])  # missed=1
        self.assertEqual(len(tracker.all_tracks), 1)
        tracker.update([])  # missed=2 => evicted
        self.assertEqual(len(tracker.all_tracks), 0)

    def test_identity_persists_through_miss_and_recovery(self):
        tracker = Tracker(max_missed=3)
        tracker.update([_det()])
        original_id = tracker.all_tracks[0].track_id
        tracker.update([])  # 1 miss
        tracker.update([_det()])  # re-matched
        self.assertEqual(tracker.active_tracks[0].track_id, original_id)

    def test_invalid_iou_threshold_raises(self):
        with self.assertRaises(ValueError):
            Tracker(iou_threshold=0.0)

    def test_invalid_max_missed_raises(self):
        with self.assertRaises(ValueError):
            Tracker(max_missed=0)


if __name__ == "__main__":
    unittest.main()
