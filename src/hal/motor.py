#!/usr/bin/env python3
"""Motor HAL primitives with safe startup and config-driven calibration."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple


class MotorSafetyError(Exception):
    """Raised when a motor operation violates safety constraints."""


def _get_float(name: str, default: float) -> float:
    """Read a float from the environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value to an inclusive range."""
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class VelocityCommand:
    """Requested platform velocity in linear and angular units."""

    linear_mps: float = 0.0
    angular_rps: float = 0.0


@dataclass(frozen=True)
class MotorCalibration:
    """Configuration loaded from config.env for motor limits and trim."""

    max_linear_speed: float = 0.5
    max_angular_speed: float = 1.2
    left_trim: float = 0.0
    right_trim: float = 0.0
    left_scale: float = 1.0
    right_scale: float = 1.0

    @classmethod
    def from_env(cls) -> 'MotorCalibration':
        """Load motor calibration from environment variables."""
        return cls(
            max_linear_speed=max(_get_float('MAX_LINEAR_SPEED', 0.5), 0.01),
            max_angular_speed=max(_get_float('MAX_ANGULAR_SPEED', 1.2), 0.01),
            left_trim=_get_float('HAL_MOTOR_LEFT_TRIM', 0.0),
            right_trim=_get_float('HAL_MOTOR_RIGHT_TRIM', 0.0),
            left_scale=_get_float('HAL_MOTOR_LEFT_SCALE', 1.0),
            right_scale=_get_float('HAL_MOTOR_RIGHT_SCALE', 1.0),
        )


@dataclass(frozen=True)
class MotorState:
    """Current safe motor state."""

    armed: bool = False
    last_command: VelocityCommand = field(default_factory=VelocityCommand)
    left_output: float = 0.0
    right_output: float = 0.0


class BaseMotorHAL(ABC):
    """Abstract base class for motor hardware implementations."""

    def __init__(self, calibration: Optional[MotorCalibration] = None):
        self.calibration = calibration or MotorCalibration.from_env()
        self._state = MotorState()

    def arm(self) -> None:
        """Explicitly arm motor output after boot or E-Stop reset."""
        self._state = MotorState(armed=True)

    def disarm(self) -> None:
        """Disarm motors and force a stop output."""
        self.stop()
        self._state = MotorState(armed=False)

    def stop(self) -> None:
        """Force a zero-velocity command through the HAL."""
        self._apply_outputs(0.0, 0.0)
        self._state = MotorState(
            armed=self._state.armed,
            last_command=VelocityCommand(),
            left_output=0.0,
            right_output=0.0,
        )

    def get_state(self) -> MotorState:
        """Return the current motor state snapshot."""
        return self._state

    def set_velocity(self, command: VelocityCommand) -> Tuple[float, float]:
        """Apply a safe velocity command to the motor driver."""
        if not self._state.armed:
            raise MotorSafetyError('Motors are disarmed')

        left_output, right_output = self.compute_outputs(command)
        self._apply_outputs(left_output, right_output)
        self._state = MotorState(
            armed=True,
            last_command=command,
            left_output=left_output,
            right_output=right_output,
        )
        return left_output, right_output

    def compute_outputs(self, command: VelocityCommand) -> Tuple[float, float]:
        """Convert a velocity command to normalized left/right outputs."""
        linear_norm = _clamp(
            command.linear_mps / self.calibration.max_linear_speed,
            -1.0,
            1.0,
        )
        angular_norm = _clamp(
            command.angular_rps / self.calibration.max_angular_speed,
            -1.0,
            1.0,
        )

        left_output = ((linear_norm - angular_norm) * self.calibration.left_scale) + self.calibration.left_trim
        right_output = ((linear_norm + angular_norm) * self.calibration.right_scale) + self.calibration.right_trim

        return (
            _clamp(left_output, -1.0, 1.0),
            _clamp(right_output, -1.0, 1.0),
        )

    @abstractmethod
    def _apply_outputs(self, left_output: float, right_output: float) -> None:
        """Apply normalized left/right output values to hardware or simulation."""


class SimulatedMotorHAL(BaseMotorHAL):
    """Deterministic motor HAL used until real hardware drivers are integrated."""

    def __init__(self, calibration: Optional[MotorCalibration] = None):
        super().__init__(calibration=calibration)
        self.applied_outputs = []

    def _apply_outputs(self, left_output: float, right_output: float) -> None:
        """Record motor outputs for tests and higher-level control integration."""
        self.applied_outputs.append((left_output, right_output))