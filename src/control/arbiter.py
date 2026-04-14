#!/usr/bin/env python3
"""Safety-aware control arbiter for manual teleoperation."""

import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from control.behavior import BehaviorCommand
from hal.motor import MotorSafetyError, VelocityCommand, create_motor_hal_from_env


def _get_float(name: str, default: float) -> float:
    """Read float config values with safe defaults."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    """Read integer config values with safe defaults."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp values to an inclusive range."""
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class ControlState:
    """Immutable control state snapshot exposed via API and websocket status."""

    armed: bool
    estop_latched: bool
    mode: str
    deadman_triggered: bool
    linear_mps: float
    angular_rps: float
    max_linear_speed: float
    max_angular_speed: float
    active_behavior: Optional[str]
    motor_backend: str
    motor_disabled_channels: List[int]
    motor_degraded: bool
    motor_degraded_reason: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        """Serialize to JSON-friendly dictionary."""
        return {
            'armed': self.armed,
            'estop_latched': self.estop_latched,
            'mode': self.mode,
            'deadman_triggered': self.deadman_triggered,
            'linear_mps': self.linear_mps,
            'angular_rps': self.angular_rps,
            'max_linear_speed': self.max_linear_speed,
            'max_angular_speed': self.max_angular_speed,
            'active_behavior': self.active_behavior,
            'motor_backend': self.motor_backend,
            'motor_disabled_channels': self.motor_disabled_channels,
            'motor_degraded': self.motor_degraded,
            'motor_degraded_reason': self.motor_degraded_reason,
        }


class ControlArbiter:
    """Arbiter that enforces safety before forwarding commands to motor HAL."""

    def __init__(self, motor_hal=None):
        self.motor_hal = motor_hal or create_motor_hal_from_env()
        self.max_linear_speed = max(_get_float('MAX_LINEAR_SPEED', 0.5), 0.01)
        self.max_angular_speed = max(_get_float('MAX_ANGULAR_SPEED', 1.2), 0.01)
        self.deadman_timeout_s = max(_get_int('DEADMAN_TIMEOUT_MS', 500), 1) / 1000.0
        self.manual_override_timeout_s = max(
            _get_int('MANUAL_OVERRIDE_TIMEOUT_MS', int(self.deadman_timeout_s * 1000)),
            1,
        ) / 1000.0
        self.estop_latched = False
        self.deadman_triggered = False
        self.last_heartbeat = time.monotonic()
        self.last_manual_input = 0.0
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.autonomy_command: Optional[BehaviorCommand] = None

    def get_state(self) -> ControlState:
        """Return current control state for API/UI status updates."""
        current_mode = 'disabled'
        active_behavior = None
        if self.motor_hal.get_state().armed:
            if self._manual_has_priority() or self.autonomy_command is None:
                current_mode = 'manual'
            else:
                current_mode = 'autonomous'
                active_behavior = self.autonomy_command.behavior

        return ControlState(
            armed=self.motor_hal.get_state().armed,
            estop_latched=self.estop_latched,
            mode=current_mode,
            deadman_triggered=self.deadman_triggered,
            linear_mps=self.last_linear,
            angular_rps=self.last_angular,
            max_linear_speed=self.max_linear_speed,
            max_angular_speed=self.max_angular_speed,
            active_behavior=active_behavior,
            motor_backend=self.motor_hal.backend_name(),
            motor_disabled_channels=self.motor_hal.disabled_channels(),
            motor_degraded=bool(self.motor_hal.disabled_channels()),
            motor_degraded_reason=self.motor_hal.degraded_reason(),
        )

    def arm(self) -> Dict[str, object]:
        """Arm control path unless E-Stop is latched."""
        if self.estop_latched:
            return {'status': 'blocked', 'message': 'Cannot arm while E-Stop is latched'}

        self.motor_hal.arm()
        self.deadman_triggered = False
        self.last_heartbeat = time.monotonic()
        self.last_manual_input = 0.0
        return {'status': 'armed'}

    def disarm(self) -> Dict[str, object]:
        """Disarm control path and stop all motion."""
        self.motor_hal.disarm()
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.autonomy_command = None
        return {'status': 'disarmed'}

    def engage_estop(self) -> Dict[str, object]:
        """Latch E-Stop and force immediate stop/disarm."""
        self.estop_latched = True
        self.motor_hal.disarm()
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.autonomy_command = None
        return {'status': 'estop_engaged'}

    def clear_estop(self) -> Dict[str, object]:
        """Clear E-Stop latch, keeping motors disarmed until explicit arm."""
        self.estop_latched = False
        self.deadman_triggered = False
        return {'status': 'estop_cleared'}

    def heartbeat(self) -> None:
        """Record liveness signal from active control client."""
        self.last_heartbeat = time.monotonic()

    def apply_drive(self, linear_mps: float, angular_rps: float) -> Dict[str, object]:
        """Validate and route manual drive command through motor HAL."""
        self._enforce_deadman()
        if self.estop_latched:
            return {'status': 'blocked', 'message': 'E-Stop is latched'}
        if not self.motor_hal.get_state().armed:
            return {'status': 'ignored', 'message': 'Robot is disarmed'}

        linear = _clamp(linear_mps, -self.max_linear_speed, self.max_linear_speed)
        angular = _clamp(angular_rps, -self.max_angular_speed, self.max_angular_speed)

        try:
            self.motor_hal.set_velocity(VelocityCommand(linear_mps=linear, angular_rps=angular))
        except MotorSafetyError as exc:
            return {'status': 'error', 'message': str(exc)}

        self.last_linear = linear
        self.last_angular = angular
        self.last_manual_input = time.monotonic()
        return {
            'status': 'ok',
            'linear_mps': linear,
            'angular_rps': angular,
            'mode': 'manual',
        }

    def apply_autonomy(self, command: BehaviorCommand) -> Dict[str, object]:
        """Apply autonomous behavior command unless manual control has priority."""
        self._enforce_deadman()
        self.heartbeat()
        if self.estop_latched:
            return {'status': 'blocked', 'message': 'E-Stop is latched'}
        if not self.motor_hal.get_state().armed:
            return {'status': 'ignored', 'message': 'Robot is disarmed'}
        if self._manual_has_priority():
            return {'status': 'overridden', 'message': 'manual_control_active'}

        linear = _clamp(command.linear_mps, -self.max_linear_speed, self.max_linear_speed)
        angular = _clamp(command.angular_rps, -self.max_angular_speed, self.max_angular_speed)
        try:
            self.motor_hal.set_velocity(VelocityCommand(linear_mps=linear, angular_rps=angular))
        except MotorSafetyError as exc:
            return {'status': 'error', 'message': str(exc)}

        self.autonomy_command = BehaviorCommand(
            behavior=command.behavior,
            linear_mps=linear,
            angular_rps=angular,
        )
        self.last_linear = linear
        self.last_angular = angular
        return {
            'status': 'ok',
            'mode': 'autonomous',
            'behavior': command.behavior,
            'linear_mps': linear,
            'angular_rps': angular,
        }

    def stop(self) -> Dict[str, object]:
        """Stop motion while preserving arm state."""
        self.motor_hal.stop()
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.autonomy_command = None
        return {'status': 'stopped'}

    def on_disconnect(self) -> Dict[str, object]:
        """Safety behavior when control channel disconnects."""
        self.deadman_triggered = True
        return self.stop()

    def check_safety(self) -> None:
        """Public hook for timers/loops to enforce deadman timeout."""
        self._enforce_deadman()

    def _enforce_deadman(self) -> None:
        """Stop motion if heartbeat timeout is exceeded while armed."""
        if not self.motor_hal.get_state().armed:
            return
        if (time.monotonic() - self.last_heartbeat) > self.deadman_timeout_s:
            self.deadman_triggered = True
            self.stop()

    def _manual_has_priority(self) -> bool:
        """Manual commands always outrank autonomy for a short override window."""
        if self.last_manual_input <= 0:
            return False
        return (time.monotonic() - self.last_manual_input) <= self.manual_override_timeout_s