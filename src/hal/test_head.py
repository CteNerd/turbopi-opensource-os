#!/usr/bin/env python3
"""Unit tests for camera head HAL clamping and calibration behavior."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.head import (
    HeadCalibration,
    HeadPosition,
    HeadSafetyError,
    HiwonderTurboPiHeadHAL,
    SimulatedHeadHAL,
    create_head_hal_from_env,
)


class FakeHeadBoard:
    """Test double for vendor board head-control methods."""

    def __init__(self):
        self.calls = []

    def pwm_servo_set_position(self, duration_s, data):
        self.calls.append((duration_s, data))


class TestHeadHAL(unittest.TestCase):
    """Tests for safe head pan/tilt control primitives."""

    def test_head_position_is_clamped_to_safe_range(self):
        calibration = HeadCalibration(
            pan_min_deg=-60.0,
            pan_max_deg=60.0,
            tilt_min_deg=-20.0,
            tilt_max_deg=20.0,
            pan_center_deg=0.0,
            tilt_center_deg=0.0,
        )
        hal = SimulatedHeadHAL(calibration=calibration)

        position = hal.set_position(HeadPosition(pan_deg=120.0, tilt_deg=-50.0))

        self.assertEqual(position.pan_deg, 60.0)
        self.assertEqual(position.tilt_deg, -20.0)
        self.assertEqual(hal.get_state().position.pan_deg, 60.0)
        self.assertEqual(hal.get_state().position.tilt_deg, -20.0)

    def test_center_moves_to_calibrated_center(self):
        calibration = HeadCalibration(
            pan_min_deg=-60.0,
            pan_max_deg=60.0,
            tilt_min_deg=-20.0,
            tilt_max_deg=20.0,
            pan_center_deg=5.0,
            tilt_center_deg=-3.0,
        )
        hal = SimulatedHeadHAL(calibration=calibration)

        hal.set_position(HeadPosition(pan_deg=30.0, tilt_deg=10.0))
        position = hal.center()

        self.assertEqual(position.pan_deg, 5.0)
        self.assertEqual(position.tilt_deg, -3.0)

    def test_invalid_backend_falls_back_to_sim(self):
        with patch.dict(os.environ, {'HAL_HEAD_BACKEND': 'vendor'}, clear=False):
            with patch('hal.head.HiwonderTurboPiHeadHAL', side_effect=HeadSafetyError('missing')):
                hal = create_head_hal_from_env()

        self.assertEqual(hal.backend_name(), 'sim')

    def test_factory_can_require_vendor_backend(self):
        with patch.dict(
            os.environ,
            {
                'HAL_HEAD_BACKEND': 'vendor',
                'HAL_HEAD_VENDOR_REQUIRED': 'true',
            },
            clear=False,
        ):
            with patch('hal.head.HiwonderTurboPiHeadHAL', side_effect=HeadSafetyError('missing')):
                with self.assertRaises(HeadSafetyError):
                    create_head_hal_from_env()

    def test_vendor_head_maps_degrees_to_pwm_pulses(self):
        board = FakeHeadBoard()
        calibration = HeadCalibration(
            pan_min_deg=-70.0,
            pan_max_deg=70.0,
            tilt_min_deg=-35.0,
            tilt_max_deg=35.0,
            pan_center_deg=0.0,
            tilt_center_deg=0.0,
        )
        with patch.dict(
            os.environ,
            {
                'HAL_HEAD_PAN_SERVO_ID': '2',
                'HAL_HEAD_TILT_SERVO_ID': '1',
                'HAL_HEAD_PAN_PULSE_MIN': '800',
                'HAL_HEAD_PAN_PULSE_MAX': '2200',
                'HAL_HEAD_TILT_PULSE_MIN': '1000',
                'HAL_HEAD_TILT_PULSE_MAX': '2000',
                'HAL_HEAD_MOVE_TIME_S': '0.02',
            },
            clear=False,
        ):
            hal = HiwonderTurboPiHeadHAL(calibration=calibration, board=board)

        hal.set_position(HeadPosition(pan_deg=70.0, tilt_deg=-35.0))

        duration, data = board.calls[-1]
        self.assertEqual(duration, 0.02)
        self.assertEqual(data, [[1, 1000], [2, 2200]])
        self.assertEqual(hal.backend_name(), 'vendor')


if __name__ == '__main__':
    unittest.main()
