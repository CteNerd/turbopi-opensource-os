#!/usr/bin/env python3
"""Motor HAL primitives with safe startup and config-driven calibration."""

import importlib
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple


logger = logging.getLogger(__name__)


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


def _get_int(name: str, default: int) -> int:
    """Read an integer from the environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    """Read a bool from the environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in ('1', 'true', 'yes', 'on'):
        return True
    if normalized in ('0', 'false', 'no', 'off'):
        return False
    return default


def _get_int_set(name: str) -> Set[int]:
    """Read a comma-separated list of ints from the environment."""
    value = os.environ.get(name, '').strip()
    if not value:
        return set()

    result: Set[int] = set()
    for token in value.split(','):
        token = token.strip()
        if not token:
            continue
        try:
            num = int(token)
            if 1 <= num <= 4:
                result.add(num)
            else:
                logger.warning('Ignoring out-of-range channel for %s: %s (must be 1-4)', name, num)
        except ValueError:
            logger.warning('Ignoring invalid integer token for %s: %s', name, token)
    return result


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
        try:
            self._apply_outputs(0.0, 0.0)
        except MotorSafetyError as exc:
            logger.error('Failed to stop motor output: %s', exc)
        self._state = MotorState(
            armed=self._state.armed,
            last_command=VelocityCommand(),
            left_output=0.0,
            right_output=0.0,
        )

    def get_state(self) -> MotorState:
        """Return the current motor state snapshot."""
        return self._state

    def backend_name(self) -> str:
        """Return the motor backend identifier for diagnostics."""
        return 'sim'

    def disabled_channels(self) -> List[int]:
        """Return disabled drive channels for degraded operation diagnostics."""
        return []

    def degraded_reason(self) -> Optional[str]:
        """Return optional degraded-mode reason for diagnostics."""
        return None

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


class HiwonderTurboPiMotorHAL(BaseMotorHAL):
    """Hardware-backed motor HAL for the Hiwonder TurboPi vendor SDK.

    This adapter preserves the existing left/right control contract from the
    control arbiter and maps it to four motor channels using the vendor-proven
    sign convention:
    - channel 1: left side, inverted
    - channel 2: right side, non-inverted
    - channel 3: left side, inverted
    - channel 4: right side, non-inverted
    """

    def __init__(
        self,
        calibration: Optional[MotorCalibration] = None,
        board=None,
        max_duty: Optional[int] = None,
        disabled_channels: Optional[Set[int]] = None,
        block_on_disabled_channels: Optional[bool] = None,
    ):
        super().__init__(calibration=calibration)
        self.board = board or self._build_vendor_board()
        self.max_duty = max(1, min(max_duty if max_duty is not None else _get_int('HAL_MOTOR_MAX_DUTY', 35), 100))
        self._disabled_channels = disabled_channels if disabled_channels is not None else _get_int_set('HAL_MOTOR_DISABLED_CHANNELS')
        self.block_on_disabled_channels = (
            block_on_disabled_channels
            if block_on_disabled_channels is not None
            else _get_bool('HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS', True)
        )
        self.channel_scale = {
            1: _clamp(_get_float('HAL_MOTOR_CHANNEL_SCALE_1', 1.0), 0.0, 2.0),
            2: _clamp(_get_float('HAL_MOTOR_CHANNEL_SCALE_2', 1.0), 0.0, 2.0),
            3: _clamp(_get_float('HAL_MOTOR_CHANNEL_SCALE_3', 1.0), 0.0, 2.0),
            4: _clamp(_get_float('HAL_MOTOR_CHANNEL_SCALE_4', 1.0), 0.0, 2.0),
        }
        self.applied_channel_outputs: List[List[int]] = []

    def _build_vendor_board(self):
        """Create a vendor board SDK instance with a clear error message."""
        try:
            # Add common HiwonderSDK search paths for both dev and prod environments
            sdk_search_paths = [
                '/opt/turbopi/current',  # Production: systemd service working directory
                '/home/pi/TurboPi',       # Development: vendor image default location
            ]
            for path in sdk_search_paths:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            logger.debug('Attempting to import HiwonderSDK from sys.path: %s', sys.path[:3])
            sdk = importlib.import_module('HiwonderSDK.ros_robot_controller_sdk')
            logger.debug('Successfully imported HiwonderSDK')
            board = sdk.Board()
            logger.debug('Successfully instantiated Board()')
            return board
        except ModuleNotFoundError as exc:
            logger.error('HiwonderSDK module not found in search paths. sys.path: %s', sys.path[:5])
            raise MotorSafetyError('Vendor motor SDK module not found') from exc
        except Exception as exc:
            logger.error('Failed to initialize vendor motor SDK: %s: %s', type(exc).__name__, exc)
            raise MotorSafetyError('Vendor motor SDK unavailable') from exc

    def backend_name(self) -> str:
        """Return the motor backend identifier for diagnostics."""
        return 'vendor'

    def disabled_channels(self) -> List[int]:
        """Return disabled drive channels for degraded operation diagnostics."""
        return sorted(self._disabled_channels)

    def degraded_reason(self) -> Optional[str]:
        """Describe degraded mode when channels are disabled."""
        if not self._disabled_channels:
            return None
        return f'disabled_channels:{sorted(self._disabled_channels)}'

    def _apply_outputs(self, left_output: float, right_output: float) -> None:
        """Apply left/right commands to the four vendor motor channels."""
        duty_by_channel = {
            1: int(round((-left_output) * self.max_duty)),
            2: int(round(right_output * self.max_duty)),
            3: int(round((-left_output) * self.max_duty)),
            4: int(round(right_output * self.max_duty)),
        }
        for channel in (1, 2, 3, 4):
            scaled = int(round(duty_by_channel[channel] * self.channel_scale[channel]))
            duty_by_channel[channel] = max(-self.max_duty, min(self.max_duty, scaled))

        unhealthy_channels = sorted(
            ch for ch in self._disabled_channels if abs(duty_by_channel.get(ch, 0)) > 0
        )
        if unhealthy_channels and self.block_on_disabled_channels:
            raise MotorSafetyError(
                f'Motor channel(s) disabled by configuration: {unhealthy_channels}'
            )

        if unhealthy_channels:
            logger.warning(
                'Applying zero duty to disabled motor channel(s): %s',
                unhealthy_channels,
            )
            for channel in unhealthy_channels:
                duty_by_channel[channel] = 0

        data = [[channel, duty_by_channel[channel]] for channel in (1, 2, 3, 4)]
        try:
            self.board.set_motor_duty(data)
        except Exception as exc:
            raise MotorSafetyError('Motor driver write failed') from exc

        self.applied_channel_outputs.append([duty_by_channel[1], duty_by_channel[2], duty_by_channel[3], duty_by_channel[4]])


def create_motor_hal_from_env() -> BaseMotorHAL:
    """Create a motor HAL based on runtime configuration.

    HAL_MOTOR_BACKEND options:
    - sim: deterministic simulation backend (default)
    - vendor: Hiwonder vendor SDK backend with fallback to simulation
    """
    backend = os.environ.get('HAL_MOTOR_BACKEND', 'sim').strip().lower()
    vendor_required = _get_bool('HAL_MOTOR_VENDOR_REQUIRED', False)
    logger.info(f"[HAL] Requested HAL_MOTOR_BACKEND={backend} (required={vendor_required})")
    if backend == 'vendor':
        try:
            logger.info("[HAL] Attempting to instantiate HiwonderTurboPiMotorHAL (vendor backend)")
            hal = HiwonderTurboPiMotorHAL()
            logger.info("[HAL] Successfully instantiated HiwonderTurboPiMotorHAL")
            return hal
        except MotorSafetyError as exc:
            logger.error(f"[HAL] MotorSafetyError during vendor backend instantiation: {exc}", exc_info=True)
            if vendor_required:
                logger.critical('[HAL] HAL_MOTOR_BACKEND=vendor but vendor backend is unavailable and required; raising error.')
                raise MotorSafetyError(
                    'HAL_MOTOR_BACKEND=vendor but vendor backend is unavailable while HAL_MOTOR_VENDOR_REQUIRED=true'
                ) from exc
            logger.warning('[HAL] Falling back to SimulatedMotorHAL because vendor backend is unavailable: %s', str(exc))
            return SimulatedMotorHAL()
        except Exception as exc:
            logger.error(f"[HAL] Unexpected error during vendor backend instantiation: {exc}", exc_info=True)
            if vendor_required:
                logger.critical('[HAL] HAL_MOTOR_BACKEND=vendor but vendor backend is unavailable and required; raising error.')
                raise MotorSafetyError(
                    'HAL_MOTOR_BACKEND=vendor but vendor backend is unavailable while HAL_MOTOR_VENDOR_REQUIRED=true'
                ) from exc
            logger.warning('[HAL] Falling back to SimulatedMotorHAL due to unexpected error: %s', str(exc))
            return SimulatedMotorHAL()

    if backend != 'sim':
        logger.warning('[HAL] Unknown HAL_MOTOR_BACKEND=%s (expected "sim" or "vendor"), falling back to sim', backend)

    logger.info('[HAL] Using SimulatedMotorHAL (sim backend)')
    return SimulatedMotorHAL()