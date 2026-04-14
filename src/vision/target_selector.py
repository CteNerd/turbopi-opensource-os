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

    Temporary misses are tolerated so short occlusions do not immediately
    clear selection. Selection is cleared only after repeated missing updates
    or explicit clear().
    """

    def __init__(self, max_missing_updates: int = 5) -> None:
        if max_missing_updates < 1:
            raise ValueError("max_missing_updates must be >= 1")
        self._selected_id: Optional[int] = None
        self._manual: bool = False
        self._max_missing_updates = max_missing_updates
        self._missing_updates = 0

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
        self._missing_updates = 0
        logger.info("Target manually selected: track_id=%d", track_id)

    def clear(self) -> None:
        """Release the current selection and revert to auto mode."""
        self._selected_id = None
        self._manual = False
        self._missing_updates = 0
        logger.info("Target selection cleared")

    def update(self, tracks: List[TrackedObject]) -> Optional[TrackedObject]:
        """Update selection against current active tracks; return target or None.

        - If a manual ID is held but its track is gone, clears selection.
        - If no selection, auto-picks the largest person track.
        """
        active_ids = {t.track_id for t in tracks}

        # Missing target is tolerated for short occlusions.
        if self._selected_id is not None and self._selected_id not in active_ids:
            self._missing_updates += 1
            if self._missing_updates >= self._max_missing_updates:
                logger.info(
                    "Target track %d lost for %d update(s); clearing selection",
                    self._selected_id,
                    self._missing_updates,
                )
                self._selected_id = None
                self._manual = False
                self._missing_updates = 0
            return None

        # Target present; reset occlusion counter.
        self._missing_updates = 0

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
        self._manual = False
        logger.debug("Auto-selected track %d (area=%.4f)", target.track_id, target.detection.area)
        return target
