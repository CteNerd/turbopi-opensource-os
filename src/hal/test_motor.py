#!/usr/bin/env python3
"""Unit tests for the TurboPi motor HAL."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hal.motor import (
    HiwonderTurboPiMotorHAL,
    MotorCalibration,
    MotorSafetyError,
    SimulatedMotorHAL,
    VelocityCommand,
    create_motor_hal_from_env,
)


class FakeBoard:
    """Test double for vendor board interface."""

    def __init__(self):
        self.calls = []

    def set_motor_duty(self, data):
        self.calls.append(data)


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

        self.assertEqual(left_output, 1.0)
        self.assertEqual(right_output, -0.1)
        self.assertEqual(hal.get_state().last_command.linear_mps, 1.0)

    def test_positive_angular_biases_left_side_for_right_turn(self):
        hal = SimulatedMotorHAL(
            calibration=MotorCalibration(max_linear_speed=1.0, max_angular_speed=1.0)
        )
        hal.arm()

        left_output, right_output = hal.set_velocity(
            VelocityCommand(linear_mps=0.0, angular_rps=0.5)
        )

        self.assertGreater(left_output, right_output)

    def test_stop_zeroes_outputs(self):
        hal = SimulatedMotorHAL()
        hal.arm()
        hal.set_velocity(VelocityCommand(linear_mps=0.1, angular_rps=0.1))
        hal.stop()

        self.assertEqual(hal.get_state().left_output, 0.0)
        self.assertEqual(hal.get_state().right_output, 0.0)

    def test_vendor_hal_maps_outputs_to_channels_with_expected_signs(self):
        board = FakeBoard()
        hal = HiwonderTurboPiMotorHAL(board=board, max_duty=50)
        hal.arm()

        hal.set_velocity(VelocityCommand(linear_mps=0.25, angular_rps=0.0))

        # Forward command should drive all channels with vendor sign convention.
        self.assertEqual(board.calls[-1], [[1, -25], [2, 25], [3, -25], [4, 25]])

    def test_vendor_hal_positive_angular_turns_right(self):
        board = FakeBoard()
        hal = HiwonderTurboPiMotorHAL(
            board=board,
            calibration=MotorCalibration(max_linear_speed=1.0, max_angular_speed=1.0),
            max_duty=50,
        )
        hal.arm()

        hal.set_velocity(VelocityCommand(linear_mps=0.0, angular_rps=0.5))

        self.assertEqual(board.calls[-1], [[1, -25], [2, -25], [3, -25], [4, -25]])

    def test_vendor_hal_blocks_nonzero_output_on_disabled_channel(self):
        board = FakeBoard()
        hal = HiwonderTurboPiMotorHAL(
            board=board,
            max_duty=50,
            disabled_channels={3},
            block_on_disabled_channels=True,
        )
        hal.arm()

        with self.assertRaises(MotorSafetyError):
            hal.set_velocity(VelocityCommand(linear_mps=0.2, angular_rps=0.0))

    def test_vendor_hal_zeroes_disabled_channel_when_non_blocking(self):
        board = FakeBoard()
        hal = HiwonderTurboPiMotorHAL(
            board=board,
            max_duty=50,
            disabled_channels={3},
            block_on_disabled_channels=False,
        )
        hal.arm()

        hal.set_velocity(VelocityCommand(linear_mps=0.2, angular_rps=0.0))
        self.assertEqual(board.calls[-1], [[1, -20], [2, 20], [3, 0], [4, 20]])
        self.assertEqual(hal.backend_name(), 'vendor')
        self.assertEqual(hal.disabled_channels(), [3])
        self.assertTrue(hal.degraded_reason().startswith('disabled_channels'))

    def test_factory_returns_sim_when_vendor_backend_unavailable(self):
        with patch.dict(os.environ, {'HAL_MOTOR_BACKEND': 'vendor'}, clear=False):
            with patch('hal.motor.HiwonderTurboPiMotorHAL', side_effect=MotorSafetyError('unavailable')):
                hal = create_motor_hal_from_env()

        self.assertIsInstance(hal, SimulatedMotorHAL)

    def test_factory_can_require_vendor_backend(self):
        with patch.dict(
            os.environ,
            {
                'HAL_MOTOR_BACKEND': 'vendor',
                'HAL_MOTOR_VENDOR_REQUIRED': 'true',
            },
            clear=False,
        ):
            with patch('hal.motor.HiwonderTurboPiMotorHAL', side_effect=MotorSafetyError('unavailable')):
                with self.assertRaises(MotorSafetyError):
                    create_motor_hal_from_env()

    def test_vendor_hal_applies_per_channel_scale(self):
        board = FakeBoard()
        with patch.dict(os.environ, {'HAL_MOTOR_CHANNEL_SCALE_3': '1.2'}, clear=False):
            hal = HiwonderTurboPiMotorHAL(board=board, max_duty=30)
        hal.arm()

        hal.set_velocity(VelocityCommand(linear_mps=0.3, angular_rps=0.0))
        # CH3 receives an increased absolute duty for weak/sticky wheel hardening.
        self.assertEqual(board.calls[-1], [[1, -18], [2, 18], [3, -22], [4, 18]])


if __name__ == '__main__':
    unittest.main()