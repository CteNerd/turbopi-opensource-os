#!/usr/bin/env python3
"""Target selection for the TurboPi vision pipeline.

Provides auto-selection (largest 'person' detection) and explicit
user selection by track ID for the UI control surface.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from vision.tracker import TrackedObject

logger = logging.getLogger(__name__)

_PERSON_LABEL = "person"


class TargetSelector:
    """Select and hold a target track for the follow behaviour.

    Selection modes:
    - **Auto**: choose the largest person in the frame when no target is held.
    - **Manual**: user has explicitly selected a track_id via the UI.

    The selected target is cleared when the track is evicted (not seen for
    ``max_missed`` frames as configured in the Tracker).
    """

    def __init__(self) -> None:
        self._selected_id: Optional[int] = None
        self._manual: bool = False

    @property
    def selected_id(self) -> Optional[int]:
        return self._selected_id

    @property
    def is_manual(self) -> bool:
        """True when the current selection was made explicitly by the UI."""
        return self._manual

    def select(self, track_id: int) -> None:
        """Explicitly select a target by track ID (UI-driven)."""
        self._selected_id = track_id
        self._manual = True
        logger.info("Target manually selected: track_id=%d", track_id)

    def clear(self) -> None:
        """Release the current selection and revert to auto mode."""
        self._selected_id = None
        self._manual = False
        logger.info("Target selection cleared")

    def update(self, tracks: List[TrackedObject]) -> Optional[TrackedObject]:
        """Update selection against current active tracks; return target or None.

        - If a manual ID is held but its track is gone, clears selection.
        - If no selection, auto-picks the largest person track.
        """
        active_ids = {t.track_id for t in tracks}
        was_manual = self._manual

        # Evict missing manual target.
        if self._selected_id is not None and self._selected_id not in active_ids:
            logger.info(
                "Target track %d lost; clearing selection", self._selected_id
            )
            self._selected_id = None
            self._manual = False
            if was_manual:
                # Do not auto-select when an explicit user target is lost.
                return None

        # Return explicit target if still present.
        if self._selected_id is not None:
            for track in tracks:
                if track.track_id == self._selected_id:
                    return track
            return None

        # Auto-select: largest person by bounding-box area.
        persons = [t for t in tracks if t.detection.label == _PERSON_LABEL]
        if not persons:
            return None

        target = max(persons, key=lambda t: t.detection.area)
        self._selected_id = target.track_id
        logger.debug("Auto-selected track %d (area=%.4f)", target.track_id, target.detection.area)
        return target
