#!/usr/bin/env python3
"""Camera HAL primitives used by vision features and tests."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional


class CameraError(Exception):
    """Raised when camera operations fail or are used incorrectly."""


SUPPORTED_PIXEL_FORMATS = {'rgb24'}


def _get_int(name: str, default: int) -> int:
    """Read an integer from the environment with a safe default."""
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class CameraCalibration:
    """Camera configuration and defaults loaded from config.env."""

    width: int = 640
    height: int = 480
    fps: int = 30
    pixel_format: str = 'rgb24'

    @classmethod
    def from_env(cls) -> 'CameraCalibration':
        """Load camera configuration from environment variables."""
        requested_format = os.environ.get('HAL_CAMERA_PIXEL_FORMAT', 'rgb24').lower().strip()
        pixel_format = requested_format if requested_format in SUPPORTED_PIXEL_FORMATS else 'rgb24'

        return cls(
            width=max(_get_int('HAL_CAMERA_WIDTH', 640), 1),
            height=max(_get_int('HAL_CAMERA_HEIGHT', 480), 1),
            fps=max(_get_int('HAL_CAMERA_FPS', 30), 1),
            pixel_format=pixel_format,
        )


@dataclass(frozen=True)
class CameraFrame:
    """Raw camera frame and metadata returned by the HAL."""

    data: bytes
    width: int
    height: int
    pixel_format: str
    timestamp: str


class BaseCameraHAL(ABC):
    """Abstract camera HAL with explicit open/close semantics."""

    def __init__(self, calibration: Optional[CameraCalibration] = None):
        self.calibration = calibration or CameraCalibration.from_env()
        self._opened = False

    def open(self) -> None:
        """Open the camera capture pipeline."""
        self._opened = True

    def close(self) -> None:
        """Close the camera capture pipeline."""
        self._opened = False

    def is_open(self) -> bool:
        """Return whether the HAL is ready to capture frames."""
        return self._opened

    @abstractmethod
    def get_frame(self) -> CameraFrame:
        """Return the next available frame from the camera backend."""


class FakeCameraHAL(BaseCameraHAL):
    """Simple deterministic camera implementation for tests and early integration."""

    def __init__(
        self,
        calibration: Optional[CameraCalibration] = None,
        frame_provider: Optional[Callable[[CameraCalibration], bytes]] = None,
    ):
        super().__init__(calibration=calibration)
        self._frame_provider = frame_provider or self._default_frame_provider

    def _default_frame_provider(self, calibration: CameraCalibration) -> bytes:
        """Return a black RGB frame for deterministic tests."""
        return bytes(calibration.width * calibration.height * 3)

    def get_frame(self) -> CameraFrame:
        """Capture a frame once the camera HAL has been opened."""
        if not self.is_open():
            raise CameraError('Camera is not open')

        return CameraFrame(
            data=self._frame_provider(self.calibration),
            width=self.calibration.width,
            height=self.calibration.height,
            pixel_format=self.calibration.pixel_format,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )