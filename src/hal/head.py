#!/usr/bin/env python3
"""Camera head pan/tilt HAL primitives with safe range clamping."""

import importlib
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


logger = logging.getLogger(__name__)


class HeadSafetyError(Exception):
    """Raised when a camera head operation violates safety constraints."""


def _get_float(name: str, default: float) -> float:
    """Read a float from environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    """Read an integer from environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    """Read a bool from environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in ('1', 'true', 'yes', 'on'):
        return True
    if normalized in ('0', 'false', 'no', 'off'):
        return False
    return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value to an inclusive range."""
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class HeadPosition:
    """Requested camera head pan/tilt position in degrees."""

    pan_deg: float = 0.0
    tilt_deg: float = 0.0


@dataclass(frozen=True)
class HeadCalibration:
    """Safe pan/tilt bounds and center position loaded from environment."""

    pan_min_deg: float = -70.0
    pan_max_deg: float = 70.0
    tilt_min_deg: float = -35.0
    tilt_max_deg: float = 35.0
    pan_center_deg: float = 0.0
    tilt_center_deg: float = 0.0

    @classmethod
    def from_env(cls) -> 'HeadCalibration':
        """Load head calibration from environment values."""
        pan_min = _get_float('HAL_HEAD_PAN_MIN_DEG', -70.0)
        pan_max = _get_float('HAL_HEAD_PAN_MAX_DEG', 70.0)
        tilt_min = _get_float('HAL_HEAD_TILT_MIN_DEG', -35.0)
        tilt_max = _get_float('HAL_HEAD_TILT_MAX_DEG', 35.0)

        if pan_min >= pan_max:
            logger.warning('Invalid head pan range (%s >= %s). Falling back to defaults.', pan_min, pan_max)
            pan_min, pan_max = -70.0, 70.0

        if tilt_min >= tilt_max:
            logger.warning('Invalid head tilt range (%s >= %s). Falling back to defaults.', tilt_min, tilt_max)
            tilt_min, tilt_max = -35.0, 35.0

        pan_center_raw = _get_float('HAL_HEAD_PAN_CENTER_DEG', 0.0)
        tilt_center_raw = _get_float('HAL_HEAD_TILT_CENTER_DEG', 0.0)

        return cls(
            pan_min_deg=pan_min,
            pan_max_deg=pan_max,
            tilt_min_deg=tilt_min,
            tilt_max_deg=tilt_max,
            pan_center_deg=_clamp(pan_center_raw, pan_min, pan_max),
            tilt_center_deg=_clamp(tilt_center_raw, tilt_min, tilt_max),
        )


@dataclass(frozen=True)
class HeadState:
    """Current camera head position state."""

    position: HeadPosition = field(default_factory=HeadPosition)


class BaseHeadHAL(ABC):
    """Abstract base class for camera head hardware implementations."""

    def __init__(self, calibration: Optional[HeadCalibration] = None):
        self.calibration = calibration or HeadCalibration.from_env()
        self._state = HeadState(
            position=HeadPosition(
                pan_deg=self.calibration.pan_center_deg,
                tilt_deg=self.calibration.tilt_center_deg,
            )
        )

    def backend_name(self) -> str:
        """Return backend identifier for diagnostics."""
        return 'sim'

    def get_state(self) -> HeadState:
        """Return current head state."""
        return self._state

    def center(self) -> HeadPosition:
        """Move the head to configured center."""
        return self.set_position(
            HeadPosition(
                pan_deg=self.calibration.pan_center_deg,
                tilt_deg=self.calibration.tilt_center_deg,
            )
        )

    def set_position(self, position: HeadPosition) -> HeadPosition:
        """Apply a safe clamped pan/tilt position command."""
        pan = _clamp(position.pan_deg, self.calibration.pan_min_deg, self.calibration.pan_max_deg)
        tilt = _clamp(position.tilt_deg, self.calibration.tilt_min_deg, self.calibration.tilt_max_deg)
        clamped = HeadPosition(pan_deg=pan, tilt_deg=tilt)
        self._apply_position(clamped)
        self._state = HeadState(position=clamped)
        return clamped

    @abstractmethod
    def _apply_position(self, position: HeadPosition) -> None:
        """Apply pan/tilt position to hardware or simulation backend."""


class SimulatedHeadHAL(BaseHeadHAL):
    """Deterministic camera head HAL for tests and simulation."""

    def __init__(self, calibration: Optional[HeadCalibration] = None):
        super().__init__(calibration=calibration)
        self.applied_positions = []

    def _apply_position(self, position: HeadPosition) -> None:
        """Record requested head positions for deterministic testing."""
        self.applied_positions.append((position.pan_deg, position.tilt_deg))


@dataclass(frozen=True)
class HeadPulseCalibration:
    """Pulse-domain calibration for vendor PWM servo head control."""

    pan_servo_id: int = 2
    tilt_servo_id: int = 1
    pan_pulse_min: int = 1000
    pan_pulse_max: int = 2000
    tilt_pulse_min: int = 1000
    tilt_pulse_max: int = 2000
    pan_pulse_center: int = 1500
    tilt_pulse_center: int = 1500
    move_time_s: float = 0.05

    @classmethod
    def from_env(cls) -> 'HeadPulseCalibration':
        """Load pulse-domain servo calibration from environment values."""
        pan_servo_id = max(1, min(_get_int('HAL_HEAD_PAN_SERVO_ID', 2), 6))
        tilt_servo_id = max(1, min(_get_int('HAL_HEAD_TILT_SERVO_ID', 1), 6))

        pan_pulse_min = max(500, min(_get_int('HAL_HEAD_PAN_PULSE_MIN', 1000), 2500))
        pan_pulse_max = max(500, min(_get_int('HAL_HEAD_PAN_PULSE_MAX', 2000), 2500))
        tilt_pulse_min = max(500, min(_get_int('HAL_HEAD_TILT_PULSE_MIN', 1000), 2500))
        tilt_pulse_max = max(500, min(_get_int('HAL_HEAD_TILT_PULSE_MAX', 2000), 2500))

        if pan_pulse_min >= pan_pulse_max:
            logger.warning(
                'Invalid head pan pulse range (%s >= %s). Falling back to 1000..2000.',
                pan_pulse_min,
                pan_pulse_max,
            )
            pan_pulse_min, pan_pulse_max = 1000, 2000

        if tilt_pulse_min >= tilt_pulse_max:
            logger.warning(
                'Invalid head tilt pulse range (%s >= %s). Falling back to 1000..2000.',
                tilt_pulse_min,
                tilt_pulse_max,
            )
            tilt_pulse_min, tilt_pulse_max = 1000, 2000

        centers = _read_vendor_servo_centers('/home/pi/TurboPi/servo_config.yaml')
        pan_center_default = centers.get(f'servo{pan_servo_id}', 1500)
        tilt_center_default = centers.get(f'servo{tilt_servo_id}', 1500)

        pan_pulse_center = _get_int('HAL_HEAD_PAN_PULSE_CENTER', pan_center_default)
        tilt_pulse_center = _get_int('HAL_HEAD_TILT_PULSE_CENTER', tilt_center_default)

        move_time_s = _clamp(_get_float('HAL_HEAD_MOVE_TIME_S', 0.05), 0.01, 2.0)

        return cls(
            pan_servo_id=pan_servo_id,
            tilt_servo_id=tilt_servo_id,
            pan_pulse_min=pan_pulse_min,
            pan_pulse_max=pan_pulse_max,
            tilt_pulse_min=tilt_pulse_min,
            tilt_pulse_max=tilt_pulse_max,
            pan_pulse_center=max(pan_pulse_min, min(pan_pulse_center, pan_pulse_max)),
            tilt_pulse_center=max(tilt_pulse_min, min(tilt_pulse_center, tilt_pulse_max)),
            move_time_s=move_time_s,
        )


def _read_vendor_servo_centers(path: str) -> dict:
    """Read servo center pulses from vendor servo_config.yaml when present."""
    result = {}
    if not os.path.exists(path):
        return result
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            for line in handle:
                match = re.match(r'^\s*(servo\d+)\s*:\s*(\d+)\s*$', line)
                if match:
                    result[match.group(1)] = int(match.group(2))
    except Exception:
        logger.warning('Failed reading vendor servo config at %s', path)
    return result


class HiwonderTurboPiHeadHAL(BaseHeadHAL):
    """Vendor-backed camera head HAL using Hiwonder PWM servo controls."""

    def __init__(self, calibration: Optional[HeadCalibration] = None, board=None, pulse: Optional[HeadPulseCalibration] = None):
        super().__init__(calibration=calibration)
        self.pulse = pulse or HeadPulseCalibration.from_env()
        self.board = board or self._build_vendor_board()
        self.applied_positions = []

    def backend_name(self) -> str:
        """Return backend identifier for diagnostics."""
        return 'vendor'

    def _build_vendor_board(self):
        """Create a vendor board SDK instance with clear error logging."""
        try:
            sdk_search_paths = [
                '/opt/turbopi/current',
                '/home/pi/TurboPi',
            ]
            for path in sdk_search_paths:
                if path not in sys.path:
                    sys.path.insert(0, path)

            sdk = importlib.import_module('HiwonderSDK.ros_robot_controller_sdk')
            board = sdk.Board()
            if not hasattr(board, 'pwm_servo_set_position'):
                raise HeadSafetyError('Vendor board SDK missing pwm_servo_set_position()')
            return board
        except ModuleNotFoundError as exc:
            raise HeadSafetyError('Vendor head SDK module not found') from exc
        except Exception as exc:
            if isinstance(exc, HeadSafetyError):
                raise
            raise HeadSafetyError('Vendor head SDK unavailable') from exc

    def _to_pulse(self, *, value_deg: float, deg_min: float, deg_max: float, pulse_min: int, pulse_max: int) -> int:
        """Map a clamped degree value into a servo pulse width."""
        if deg_max <= deg_min:
            raise HeadSafetyError('Invalid degree range for head mapping')
        fraction = (value_deg - deg_min) / (deg_max - deg_min)
        mapped = pulse_min + (fraction * (pulse_max - pulse_min))
        return int(round(max(pulse_min, min(mapped, pulse_max))))

    def _apply_position(self, position: HeadPosition) -> None:
        """Apply pan/tilt position through vendor PWM servo channel API."""
        tilt_pulse = self._to_pulse(
            value_deg=position.tilt_deg,
            deg_min=self.calibration.tilt_min_deg,
            deg_max=self.calibration.tilt_max_deg,
            pulse_min=self.pulse.tilt_pulse_min,
            pulse_max=self.pulse.tilt_pulse_max,
        )
        pan_pulse = self._to_pulse(
            value_deg=position.pan_deg,
            deg_min=self.calibration.pan_min_deg,
            deg_max=self.calibration.pan_max_deg,
            pulse_min=self.pulse.pan_pulse_min,
            pulse_max=self.pulse.pan_pulse_max,
        )

        data = [
            [self.pulse.tilt_servo_id, tilt_pulse],
            [self.pulse.pan_servo_id, pan_pulse],
        ]
        try:
            self.board.pwm_servo_set_position(self.pulse.move_time_s, data)
        except Exception as exc:
            raise HeadSafetyError('Head PWM servo write failed') from exc

        self.applied_positions.append((position.pan_deg, position.tilt_deg, pan_pulse, tilt_pulse))


def create_head_hal_from_env() -> BaseHeadHAL:
    """Create camera head HAL from environment configuration.

    HAL_HEAD_BACKEND options:
    - sim: deterministic simulation backend (default)
    - vendor: Hiwonder PWM-servo backend with fallback to simulation
    """
    backend = os.environ.get('HAL_HEAD_BACKEND', 'sim').strip().lower()
    vendor_required = _get_bool('HAL_HEAD_VENDOR_REQUIRED', False)
    if backend == 'vendor':
        try:
            return HiwonderTurboPiHeadHAL()
        except HeadSafetyError as exc:
            if vendor_required:
                raise HeadSafetyError(
                    'HAL_HEAD_BACKEND=vendor but vendor backend is unavailable while HAL_HEAD_VENDOR_REQUIRED=true'
                ) from exc
            logger.warning('Falling back to SimulatedHeadHAL because vendor backend is unavailable: %s', str(exc))
            return SimulatedHeadHAL()

    if backend != 'sim':
        logger.warning('Unknown HAL_HEAD_BACKEND=%s (expected "sim" or "vendor"), falling back to sim', backend)
    return SimulatedHeadHAL()
