#!/usr/bin/env python3
"""Unit tests for the TurboPi camera HAL."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.camera import CameraCalibration, CameraError, FakeCameraHAL


class TestCameraHAL(unittest.TestCase):
    """Tests for camera configuration and frame capture."""

    def test_camera_calibration_loads_from_env(self):
        with patch.dict(os.environ, {
            'HAL_CAMERA_WIDTH': '320',
            'HAL_CAMERA_HEIGHT': '240',
            'HAL_CAMERA_FPS': '15',
            'HAL_CAMERA_PIXEL_FORMAT': 'rgb24',
        }, clear=False):
            calibration = CameraCalibration.from_env()

        self.assertEqual(calibration.width, 320)
        self.assertEqual(calibration.height, 240)
        self.assertEqual(calibration.fps, 15)
        self.assertEqual(calibration.pixel_format, 'rgb24')

    def test_camera_must_be_open_before_capture(self):
        hal = FakeCameraHAL()

        with self.assertRaises(CameraError):
            hal.get_frame()

    def test_camera_returns_frame_metadata(self):
        calibration = CameraCalibration(width=4, height=2, fps=10, pixel_format='rgb24')
        hal = FakeCameraHAL(calibration=calibration)
        hal.open()
        frame = hal.get_frame()

        self.assertEqual(frame.width, 4)
        self.assertEqual(frame.height, 2)
        self.assertEqual(frame.pixel_format, 'rgb24')
        self.assertEqual(len(frame.data), 24)


if __name__ == '__main__':
    unittest.main()