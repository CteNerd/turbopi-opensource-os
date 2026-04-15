#!/usr/bin/env python3
"""Unit tests for control arbiter safety state transitions."""

import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from control.arbiter import ControlArbiter
from control.behavior import BehaviorCommand
from hal.motor import SimulatedMotorHAL


class TestControlArbiter(unittest.TestCase):
    """Safety-focused control arbiter tests."""

    def setUp(self):
        patcher = patch.dict(os.environ, {
            'MAX_LINEAR_SPEED': '0.5',
            'MAX_ANGULAR_SPEED': '1.2',
            'DEADMAN_TIMEOUT_MS': '50',
            'MANUAL_OVERRIDE_TIMEOUT_MS': '120',
        }, clear=False)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.arbiter = ControlArbiter(motor_hal=SimulatedMotorHAL())

    def test_arm_disarm_state_transition(self):
        self.assertFalse(self.arbiter.get_state().armed)
        self.assertEqual(self.arbiter.arm()['status'], 'armed')
        self.assertTrue(self.arbiter.get_state().armed)
        self.assertEqual(self.arbiter.disarm()['status'], 'disarmed')
        self.assertFalse(self.arbiter.get_state().armed)

    def test_default_constructor_uses_motor_hal_factory(self):
        with patch('control.arbiter.create_motor_hal_from_env', return_value=SimulatedMotorHAL()) as factory:
            arbiter = ControlArbiter()

        factory.assert_called_once()
        self.assertIsNotNone(arbiter.motor_hal)

    def test_control_state_includes_motor_diagnostics(self):
        state = self.arbiter.get_state().to_dict()
        self.assertEqual(state.get('motor_backend'), 'sim')
        self.assertEqual(state.get('motor_disabled_channels'), [])
        self.assertFalse(state.get('motor_degraded'))
        self.assertIsNone(state.get('motor_degraded_reason'))
        self.assertEqual(state.get('head_backend'), 'sim')
        self.assertIn('head_pan_deg', state)
        self.assertIn('head_tilt_deg', state)
        self.assertIn('head_pan_min_deg', state)
        self.assertIn('head_pan_max_deg', state)
        self.assertIn('head_tilt_min_deg', state)
        self.assertIn('head_tilt_max_deg', state)

    def test_estop_blocks_arm_until_cleared(self):
        self.arbiter.engage_estop()
        result = self.arbiter.arm()
        self.assertEqual(result['status'], 'blocked')
        self.arbiter.clear_estop()
        self.assertEqual(self.arbiter.arm()['status'], 'armed')

    def test_speed_limits_are_enforced(self):
        self.arbiter.arm()
        result = self.arbiter.apply_drive(99.0, -99.0)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['linear_mps'], 0.5)
        self.assertEqual(result['angular_rps'], -1.2)

    def test_deadman_timeout_triggers_stop(self):
        self.arbiter.arm()
        self.arbiter.apply_drive(0.2, 0.1)
        time.sleep(0.08)
        self.arbiter.check_safety()
        state = self.arbiter.get_state()
        self.assertTrue(state.deadman_triggered)
        self.assertEqual(state.linear_mps, 0.0)
        self.assertEqual(state.angular_rps, 0.0)

    def test_disconnect_triggers_immediate_stop(self):
        self.arbiter.arm()
        self.arbiter.apply_drive(0.2, 0.1)
        self.arbiter.on_disconnect()
        self.assertEqual(self.arbiter.get_state().linear_mps, 0.0)
        self.assertTrue(self.arbiter.get_state().deadman_triggered)

    def test_autonomy_command_applies_when_manual_inactive(self):
        self.arbiter.arm()
        result = self.arbiter.apply_autonomy(
            BehaviorCommand(behavior='follow', linear_mps=0.2, angular_rps=-0.1)
        )
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['mode'], 'autonomous')

        state = self.arbiter.get_state()
        self.assertEqual(state.mode, 'autonomous')
        self.assertEqual(state.active_behavior, 'follow')

    def test_manual_control_overrides_autonomy(self):
        self.arbiter.arm()
        self.arbiter.apply_drive(0.1, 0.0)
        result = self.arbiter.apply_autonomy(
            BehaviorCommand(behavior='follow', linear_mps=0.2, angular_rps=0.2)
        )
        self.assertEqual(result['status'], 'overridden')

        state = self.arbiter.get_state()
        self.assertEqual(state.mode, 'manual')
        self.assertIsNone(state.active_behavior)

    def test_autonomy_allowed_after_manual_override_window(self):
        self.arbiter.arm()
        self.arbiter.apply_drive(0.1, 0.0)
        time.sleep(0.13)
        self.arbiter.heartbeat()

        result = self.arbiter.apply_autonomy(
            BehaviorCommand(behavior='follow', linear_mps=0.2, angular_rps=0.1)
        )
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['behavior'], 'follow')

    def test_head_commands_are_clamped_to_safe_limits(self):
        result = self.arbiter.apply_head(999.0, -999.0)
        self.assertEqual(result['status'], 'ok')
        state = self.arbiter.get_state()
        self.assertEqual(result['pan_deg'], state.head_pan_max_deg)
        self.assertEqual(result['tilt_deg'], state.head_tilt_min_deg)

    def test_head_commands_blocked_when_estop_latched(self):
        self.arbiter.engage_estop()
        result = self.arbiter.apply_head(10.0, -5.0)
        self.assertEqual(result['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()