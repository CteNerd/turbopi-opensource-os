#!/usr/bin/env python3
"""Per-frame object tracker with persistent identity assignment.

Uses IoU-based greedy matching to assign stable integer IDs to detections
across frames, with configurable lost-target eviction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vision.detection import Detection

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """A detection annotated with a persistent track ID."""

    track_id: int
    detection: Detection
    # Number of consecutive frames this object has been seen.
    age: int = 1
    # Number of consecutive frames this object has been missing.
    missed_frames: int = 0


def _iou(a: Detection, b: Detection) -> float:
    """Compute Intersection-over-Union of two bounding boxes."""
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)

    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter_area = inter_w * inter_h

    union_area = a.area + b.area - inter_area
    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


class Tracker:
    """Greedy IoU tracker assigning persistent IDs to detected objects.

    Args:
        iou_threshold:   Minimum IoU to match a detection to an existing track.
        max_missed:      Evict a track after it has been absent this many frames.
    """

    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 5) -> None:
        if not (0.0 < iou_threshold <= 1.0):
            raise ValueError("iou_threshold must be in (0.0, 1.0]")
        if max_missed < 1:
            raise ValueError("max_missed must be >= 1")

        self._iou_threshold = iou_threshold
        self._max_missed = max_missed
        self._tracks: Dict[int, TrackedObject] = {}
        self._next_id: int = 1

    @property
    def active_tracks(self) -> List[TrackedObject]:
        """Currently tracked objects (missed_frames == 0)."""
        return [t for t in self._tracks.values() if t.missed_frames == 0]

    @property
    def all_tracks(self) -> List[TrackedObject]:
        return list(self._tracks.values())

    def update(self, detections: List[Detection]) -> List[TrackedObject]:
        """Match detections to existing tracks; create new tracks for unmatched.

        Returns the list of tracks that have an active detection this frame.
        """
        # Mark all tracks as missed initially.
        for track in self._tracks.values():
            track.missed_frames += 1

        unmatched_detections = list(detections)

        for track in self._tracks.values():
            if not unmatched_detections:
                break
            best_iou = 0.0
            best_det: Optional[Detection] = None
            for det in unmatched_detections:
                score = _iou(track.detection, det)
                if score > best_iou:
                    best_iou = score
                    best_det = det

            if best_det is not None and best_iou >= self._iou_threshold:
                track.detection = best_det
                track.missed_frames = 0
                track.age += 1
                unmatched_detections.remove(best_det)
                logger.debug("Track %d matched (IoU=%.2f)", track.track_id, best_iou)

        # New tracks for unmatched detections.
        for det in unmatched_detections:
            new_track = TrackedObject(track_id=self._next_id, detection=det)
            self._tracks[self._next_id] = new_track
            logger.debug("New track %d created", self._next_id)
            self._next_id += 1

        # Evict stale tracks.
        stale = [tid for tid, t in self._tracks.items() if t.missed_frames > self._max_missed]
        for tid in stale:
            logger.debug("Track %d evicted (missed %d frames)", tid, self._tracks[tid].missed_frames)
            del self._tracks[tid]

        return self.active_tracks
