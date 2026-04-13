#!/usr/bin/env python3
"""Unit tests for the TurboPi motor HAL."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.motor import MotorCalibration, MotorSafetyError, SimulatedMotorHAL, VelocityCommand


class TestMotorCalibration(unittest.TestCase):
    """Tests for calibration loading and velocity normalization."""

    def test_calibration_loads_from_env(self):
        with patch.dict(os.environ, {
            'MAX_LINEAR_SPEED': '0.8',
            'MAX_ANGULAR_SPEED': '2.0',
            'HAL_MOTOR_LEFT_TRIM': '0.1',
            'HAL_MOTOR_RIGHT_TRIM': '-0.1',
            'HAL_MOTOR_LEFT_SCALE': '0.9',
            'HAL_MOTOR_RIGHT_SCALE': '1.1',
        }, clear=False):
            calibration = MotorCalibration.from_env()

        self.assertEqual(calibration.max_linear_speed, 0.8)
        self.assertEqual(calibration.max_angular_speed, 2.0)
        self.assertEqual(calibration.left_trim, 0.1)
        self.assertEqual(calibration.right_trim, -0.1)
        self.assertEqual(calibration.left_scale, 0.9)
        self.assertEqual(calibration.right_scale, 1.1)

    def test_safe_startup_is_disarmed(self):
        hal = SimulatedMotorHAL()
        self.assertFalse(hal.get_state().armed)

    def test_disarmed_motor_rejects_motion(self):
        hal = SimulatedMotorHAL()
        with self.assertRaises(MotorSafetyError):
            hal.set_velocity(VelocityCommand(linear_mps=0.2))

    def test_velocity_outputs_are_clamped_and_calibrated(self):
        calibration = MotorCalibration(
            max_linear_speed=0.5,
            max_angular_speed=1.0,
            left_trim=0.1,
            right_trim=-0.1,
            left_scale=1.0,
            right_scale=1.0,
        )
        hal = SimulatedMotorHAL(calibration=calibration)
        hal.arm()

        left_output, right_output = hal.set_velocity(
            VelocityCommand(linear_mps=1.0, angular_rps=1.0)
        )

        self.assertEqual(left_output, 0.1)
        self.assertEqual(right_output, 1.0)
        self.assertEqual(hal.get_state().last_command.linear_mps, 1.0)

    def test_stop_zeroes_outputs(self):
        hal = SimulatedMotorHAL()
        hal.arm()
        hal.set_velocity(VelocityCommand(linear_mps=0.1, angular_rps=0.1))
        hal.stop()

        self.assertEqual(hal.get_state().left_output, 0.0)
        self.assertEqual(hal.get_state().right_output, 0.0)


if __name__ == '__main__':
    unittest.main()