#!/usr/bin/env python3
"""Unit tests for websocket control bridge routing."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from control.arbiter import ControlArbiter
from control.websocket_control import ControlWebSocketBridge
from hal.motor import SimulatedMotorHAL


class TestControlWebSocketBridge(unittest.TestCase):
    """Tests websocket message routing and disconnect stop behavior."""

    def setUp(self):
        patcher = patch.dict(os.environ, {'DEADMAN_TIMEOUT_MS': '200'}, clear=False)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.arbiter = ControlArbiter(motor_hal=SimulatedMotorHAL())
        self.bridge = ControlWebSocketBridge(self.arbiter)
        self.connection_id = 1
        self.bridge.connect(self.connection_id)

    def test_heartbeat_message(self):
        result = self.bridge.handle_text(self.connection_id, '{"type":"heartbeat"}')
        self.assertEqual(result['status'], 'ok')

    def test_drive_message_requires_arm(self):
        result = self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":0.1,"angular":0.2}')
        self.assertEqual(result['status'], 'ignored')

    def test_drive_message_after_arm(self):
        self.arbiter.arm()
        result = self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":0.1,"angular":0.2}')
        self.assertEqual(result['status'], 'ok')

    def test_disconnect_triggers_stop(self):
        self.arbiter.arm()
        self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":0.1,"angular":0.2}')
        result = self.bridge.disconnect(self.connection_id)
        self.assertEqual(result['status'], 'stopped')

    def test_new_connection_forces_previous_stop(self):
        self.arbiter.arm()
        self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":0.1,"angular":0.2}')
        self.bridge.connect(2)
        state = self.arbiter.get_state()
        self.assertEqual(state.linear_mps, 0.0)
        self.assertEqual(state.angular_rps, 0.0)

    def test_on_disconnect_latches_deadman_triggered(self):
        # Verify on_disconnect() latches deadman before any new-connection heartbeat resets it.
        # (connect() intentionally calls heartbeat() afterwards to set up the new session.)
        self.arbiter.arm()
        self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":0.1,"angular":0.2}')
        self.arbiter.on_disconnect()
        state = self.arbiter.get_state()
        self.assertTrue(state.deadman_triggered)
        self.assertEqual(state.linear_mps, 0.0)
        self.assertEqual(state.angular_rps, 0.0)

    def test_invalid_drive_values_are_rejected(self):
        self.arbiter.arm()
        result = self.bridge.handle_text(self.connection_id, '{"type":"drive","linear":"fast","angular":0.2}')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'invalid_drive_values')

    def test_head_message_updates_camera_head(self):
        result = self.bridge.handle_text(self.connection_id, '{"type":"head","pan_deg":12.0,"tilt_deg":-7.0}')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['pan_deg'], 12.0)
        self.assertEqual(result['tilt_deg'], -7.0)

    def test_head_message_center(self):
        self.bridge.handle_text(self.connection_id, '{"type":"head","pan_deg":20.0,"tilt_deg":10.0}')
        result = self.bridge.handle_text(self.connection_id, '{"type":"head","center":true}')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['pan_deg'], 0.0)
        self.assertEqual(result['tilt_deg'], 0.0)

    def test_invalid_head_values_are_rejected(self):
        result = self.bridge.handle_text(self.connection_id, '{"type":"head","pan_deg":"left","tilt_deg":0.0}')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'invalid_head_values')


if __name__ == '__main__':
    unittest.main()