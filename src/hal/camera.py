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


class OpenCVCameraHAL(BaseCameraHAL):
    """OpenCV camera backend that returns JPEG-encoded frames for MJPEG streaming."""

    def __init__(self, calibration: Optional[CameraCalibration] = None, device_index: int = -1):
        super().__init__(calibration=calibration)
        self.device_index = device_index
        self._capture = None

    def open(self) -> None:
        """Open camera device via OpenCV and apply basic calibration hints."""
        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise CameraError('OpenCV (cv2) not available') from exc

        capture = cv2.VideoCapture(self.device_index)
        if not capture or not capture.isOpened():
            raise CameraError(f'Failed to open camera device index {self.device_index}')

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.calibration.width))
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.calibration.height))
        capture.set(cv2.CAP_PROP_FPS, float(self.calibration.fps))

        self._capture = capture
        self._opened = True

    def close(self) -> None:
        """Release camera capture resources."""
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
        self._capture = None
        self._opened = False

    def get_frame(self) -> CameraFrame:
        """Capture and JPEG-encode one frame."""
        if not self.is_open() or self._capture is None:
            raise CameraError('Camera is not open')

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError('Failed to read frame from camera')

        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise CameraError('OpenCV (cv2) not available') from exc

        encoded_ok, encoded = cv2.imencode('.jpg', frame)
        if not encoded_ok:
            raise CameraError('Failed to encode frame as JPEG')

        height, width = frame.shape[:2]
        return CameraFrame(
            data=encoded.tobytes(),
            width=width,
            height=height,
            pixel_format='jpeg',
            timestamp=datetime.now(timezone.utc).isoformat(),
        )