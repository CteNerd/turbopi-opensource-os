#!/usr/bin/env python3
"""Unit tests for target selection (auto and manual modes)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vision.detection import Detection
from vision.tracker import TrackedObject
from vision.target_selector import TargetSelector


def _track(track_id: int, label: str = "person", x1=0.2, y1=0.1, x2=0.8, y2=0.9) -> TrackedObject:
    det = Detection(label=label, confidence=0.85, x1=x1, y1=y1, x2=x2, y2=y2)
    return TrackedObject(track_id=track_id, detection=det)


class TestTargetSelector(unittest.TestCase):
    def test_auto_selects_largest_person(self):
        selector = TargetSelector()
        small = _track(1, x1=0.4, y1=0.4, x2=0.6, y2=0.6)
        large = _track(2, x1=0.1, y1=0.1, x2=0.9, y2=0.9)
        target = selector.update([small, large])
        self.assertIsNotNone(target)
        self.assertEqual(target.track_id, 2)

    def test_auto_ignores_non_person_labels(self):
        selector = TargetSelector()
        chair = _track(1, label="chair")
        target = selector.update([chair])
        self.assertIsNone(target)

    def test_manual_select_overrides_auto(self):
        selector = TargetSelector()
        small = _track(1, x1=0.4, y1=0.4, x2=0.6, y2=0.6)
        large = _track(2, x1=0.1, y1=0.1, x2=0.9, y2=0.9)
        selector.select(1)
        target = selector.update([small, large])
        self.assertEqual(target.track_id, 1)
        self.assertTrue(selector.is_manual)

    def test_manual_selection_cleared_when_track_lost(self):
        selector = TargetSelector(max_missing_updates=1)
        selector.select(5)
        target = selector.update([_track(1)])
        self.assertIsNone(target)
        self.assertIsNone(selector.selected_id)
        self.assertFalse(selector.is_manual)

    def test_manual_selection_persists_through_temporary_miss(self):
        selector = TargetSelector(max_missing_updates=3)
        manual = _track(5)

        selector.select(5)
        self.assertEqual(selector.update([manual]).track_id, 5)

        # Single missed update should not clear manual selection.
        self.assertIsNone(selector.update([]))
        self.assertEqual(selector.selected_id, 5)
        self.assertTrue(selector.is_manual)

        # Target reacquired within tolerance keeps same identity.
        self.assertEqual(selector.update([manual]).track_id, 5)

    def test_auto_selection_persists_through_temporary_miss(self):
        selector = TargetSelector(max_missing_updates=3)
        auto = _track(2, x1=0.1, y1=0.1, x2=0.9, y2=0.9)

        first = selector.update([auto])
        self.assertIsNotNone(first)
        self.assertEqual(first.track_id, 2)
        self.assertFalse(selector.is_manual)

        # Single miss should not clear selected id.
        self.assertIsNone(selector.update([]))
        self.assertEqual(selector.selected_id, 2)

        # Reappearance preserves target id.
        second = selector.update([auto])
        self.assertIsNotNone(second)
        self.assertEqual(second.track_id, 2)

    def test_selection_clears_after_miss_tolerance(self):
        selector = TargetSelector(max_missing_updates=2)
        auto = _track(2)

        selector.update([auto])
        self.assertEqual(selector.selected_id, 2)
        selector.update([])  # first miss retained
        self.assertEqual(selector.selected_id, 2)
        selector.update([])  # second miss clears
        self.assertIsNone(selector.selected_id)

    def test_clear_reverts_to_auto(self):
        selector = TargetSelector()
        large = _track(2, x1=0.1, y1=0.1, x2=0.9, y2=0.9)
        selector.select(99)
        selector.clear()
        self.assertFalse(selector.is_manual)
        target = selector.update([large])
        self.assertEqual(target.track_id, 2)

    def test_no_tracks_returns_none(self):
        selector = TargetSelector()
        self.assertIsNone(selector.update([]))

    def test_identity_persists_across_frames(self):
        selector = TargetSelector()
        track = _track(3)
        selector.update([track])
        first_id = selector.selected_id
        selector.update([track])
        self.assertEqual(selector.selected_id, first_id)


if __name__ == "__main__":
    unittest.main()
