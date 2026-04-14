#!/usr/bin/env python3
"""Follow behavior controller for autonomous target following.

This module converts target observations into smooth velocity commands and
never bypasses the control arbiter.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from control.behavior import BehaviorCommand


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class TargetObservation:
    """Normalized target observation from vision runtime.

    Attributes:
        target_id: Track id of observed target.
        center_x: Horizontal center in [0.0, 1.0]. 0.5 is image center.
        area: Normalized bounding-box area in [0.0, 1.0].
        timestamp: Monotonic timestamp when observed.
    """

    target_id: int
    center_x: float
    area: float
    timestamp: float


class FollowBehavior:
    """Stateful follow controller with smoothing and lost-target handling."""

    def __init__(
        self,
        *,
        desired_area: float = 0.16,
        linear_kp: float = 1.1,
        angular_kp: float = 2.0,
        dead_zone_x: float = 0.04,
        dead_zone_area: float = 0.015,
        smooth_alpha: float = 0.35,
        max_linear_mps: float = 0.30,
        max_angular_rps: float = 1.0,
        target_timeout_s: float = 0.8,
    ) -> None:
        self._desired_area = desired_area
        self._linear_kp = linear_kp
        self._angular_kp = angular_kp
        self._dead_zone_x = dead_zone_x
        self._dead_zone_area = dead_zone_area
        self._smooth_alpha = smooth_alpha
        self._max_linear_mps = max_linear_mps
        self._max_angular_rps = max_angular_rps
        self._target_timeout_s = target_timeout_s

        self._lock = threading.Lock()
        self._enabled = False
        self._target_id: Optional[int] = None
        self._observation: Optional[TargetObservation] = None
        self._lost_target = False
        self._linear = 0.0
        self._angular = 0.0

    def start(self, target_id: Optional[int]) -> dict:
        """Enable follow behavior for an optional target id."""
        with self._lock:
            self._enabled = True
            self._target_id = target_id
            self._lost_target = False
        return {'status': 'started', 'target_id': target_id}

    def stop(self) -> dict:
        """Disable follow behavior and clear output state."""
        with self._lock:
            self._enabled = False
            self._lost_target = False
            self._linear = 0.0
            self._angular = 0.0
        return {'status': 'stopped'}

    def update_observation(self, observation: TargetObservation) -> bool:
        """Record the latest target observation.

        Returns True if the observation was accepted for control, False when
        ignored (for example mismatched target id while a specific target is set).
        """
        with self._lock:
            if self._target_id is not None and observation.target_id != self._target_id:
                return False
            self._observation = observation
            self._lost_target = False
            return True

    def state(self) -> dict:
        with self._lock:
            return {
                'enabled': self._enabled,
                'target_id': self._target_id,
                'lost_target': self._lost_target,
                'linear_mps': self._linear,
                'angular_rps': self._angular,
            }

    def next_command(self, now: Optional[float] = None) -> Optional[BehaviorCommand]:
        """Compute the next smoothed follow command."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if not self._enabled:
                return None

            raw_linear = 0.0
            raw_angular = 0.0

            if self._observation is None or (now - self._observation.timestamp) > self._target_timeout_s:
                self._lost_target = True
                self._linear = 0.0
                self._angular = 0.0
                return BehaviorCommand(
                    behavior='follow',
                    linear_mps=0.0,
                    angular_rps=0.0,
                )
            else:
                self._lost_target = False
                x_error = self._observation.center_x - 0.5
                if abs(x_error) < self._dead_zone_x:
                    x_error = 0.0

                area_error = self._desired_area - self._observation.area
                if abs(area_error) < self._dead_zone_area:
                    area_error = 0.0

                raw_linear = _clamp(
                    self._linear_kp * area_error,
                    -self._max_linear_mps,
                    self._max_linear_mps,
                )
                raw_angular = _clamp(
                    self._angular_kp * x_error,
                    -self._max_angular_rps,
                    self._max_angular_rps,
                )

            # Exponential smoothing to reduce abrupt velocity changes.
            self._linear = (self._smooth_alpha * raw_linear) + ((1.0 - self._smooth_alpha) * self._linear)
            self._angular = (self._smooth_alpha * raw_angular) + ((1.0 - self._smooth_alpha) * self._angular)

            if abs(self._linear) < 1e-3:
                self._linear = 0.0
            if abs(self._angular) < 1e-3:
                self._angular = 0.0

            return BehaviorCommand(
                behavior='follow',
                linear_mps=self._linear,
                angular_rps=self._angular,
            )
