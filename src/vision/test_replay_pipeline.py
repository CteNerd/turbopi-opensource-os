#!/usr/bin/env python3
"""Replay tests for the vision detection->tracking->target selection pipeline."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vision.detection import Detection
from vision.target_selector import TargetSelector
from vision.tracker import Tracker


class TestVisionReplayPipeline(unittest.TestCase):
    def test_replay_keeps_target_through_short_occlusion(self):
        tracker = Tracker(iou_threshold=0.25, max_missed=4)
        selector = TargetSelector(max_missing_updates=3)

        replay_frames = [
            [Detection('person', 0.93, 0.40, 0.20, 0.62, 0.88)],
            [Detection('person', 0.94, 0.41, 0.20, 0.63, 0.88)],
            [],
            [Detection('person', 0.91, 0.43, 0.21, 0.65, 0.89)],
        ]

        selected_ids = []
        for detections in replay_frames:
            active_tracks = tracker.update(detections)
            target = selector.update(active_tracks)
            selected_ids.append(target.track_id if target else None)

        self.assertEqual(selected_ids[0], selected_ids[1])
        self.assertIsNone(selected_ids[2])
        self.assertEqual(selected_ids[3], selected_ids[0])

    def test_replay_prefers_largest_person_when_auto_selecting(self):
        tracker = Tracker(iou_threshold=0.2, max_missed=3)
        selector = TargetSelector(max_missing_updates=2)

        frame = [
            Detection('person', 0.90, 0.10, 0.20, 0.22, 0.55),
            Detection('person', 0.92, 0.50, 0.18, 0.90, 0.94),
            Detection('dog', 0.97, 0.20, 0.20, 0.50, 0.60),
        ]

        active_tracks = tracker.update(frame)
        target = selector.update(active_tracks)

        self.assertIsNotNone(target)
        self.assertEqual(target.detection.label, 'person')
        # Larger person is centered to the right in this replay frame.
        self.assertGreater(target.detection.cx, 0.6)


if __name__ == '__main__':
    unittest.main()
