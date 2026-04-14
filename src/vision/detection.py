#!/usr/bin/env python3
"""Interval-based object detection for the TurboPi vision pipeline.

Runs a detector callback every N frames against raw HAL frames.
A mock detector is provided so the module is fully testable without
any camera hardware or model binaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List

from hal.camera import CameraFrame

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    """A single detected object in a frame."""

    label: str
    confidence: float
    # Normalised bounding box: x1, y1, x2, y2 in [0.0, 1.0]
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def cx(self) -> float:
        """Horizontal centre of bounding box (normalised)."""
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        """Vertical centre of bounding box (normalised)."""
        return (self.y1 + self.y2) / 2.0

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height


# Detector callable type: takes a CameraFrame, returns list of Detections.
DetectorFn = Callable[[CameraFrame], List[Detection]]


class DetectionEngine:
    """Run object detection at a fixed frame interval.

    Args:
        detector_fn:    Callable that takes a CameraFrame and returns detections.
        interval_frames: Run the detector once every N frames (default: 1 = every frame).
        min_confidence:  Drop detections below this threshold.
    """

    def __init__(
        self,
        detector_fn: DetectorFn,
        interval_frames: int = 1,
        min_confidence: float = 0.3,
    ) -> None:
        if interval_frames < 1:
            raise ValueError("interval_frames must be >= 1")
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("min_confidence must be in [0.0, 1.0]")

        self._detector_fn = detector_fn
        self._interval = interval_frames
        self._min_confidence = min_confidence

        # Initialise so the very first frame triggers detection.
        self._frame_count: int = interval_frames - 1
        self._last_detections: List[Detection] = []

    @property
    def last_detections(self) -> List[Detection]:
        """Most recent detection results (may be from a prior interval)."""
        return list(self._last_detections)

    def process_frame(self, frame: CameraFrame) -> List[Detection]:
        """Process one frame; detector runs only on interval boundaries.

        Returns the current detection list (cached between intervals).
        """
        self._frame_count += 1
        if self._frame_count % self._interval == 0:
            raw = self._detector_fn(frame)
            self._last_detections = [
                d for d in raw if d.confidence >= self._min_confidence
            ]
            logger.debug(
                "Detection ran on frame %d: %d result(s)",
                self._frame_count,
                len(self._last_detections),
            )
        return list(self._last_detections)


# ---------------------------------------------------------------------------
# Mock detector for testing and offline development
# ---------------------------------------------------------------------------

def mock_person_detector(frame: CameraFrame) -> List[Detection]:
    """Deterministic detector that returns one centred 'person' detection."""
    return [
        Detection(
            label="person",
            confidence=0.85,
            x1=0.3,
            y1=0.1,
            x2=0.7,
            y2=0.9,
        )
    ]
