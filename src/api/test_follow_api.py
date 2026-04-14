#!/usr/bin/env python3
"""Integration tests for follow behavior API endpoints."""

import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestFollowAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18085'
        os.environ['UI_PORT'] = '8081'

        # Reset singletons to isolate behavior from other test modules.
        APIHandler._control_arbiter = None
        APIHandler._camera_hal = None
        APIHandler._follow_behavior = None
        APIHandler._follow_thread_started = False

        cls.server = HTTPServer(('localhost', 18085), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18085'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _post_json(self, path, payload=None, with_origin=True):
        body = b'' if payload is None else json.dumps(payload).encode('utf-8')

        def _send_once():
            req = urllib.request.Request(f'{self.base}{path}', data=body, method='POST')
            if payload is not None:
                req.add_header('Content-Type', 'application/json')
            if with_origin:
                req.add_header('Origin', 'http://localhost:8081')
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = response.read().decode()
                return response.status, json.loads(raw) if raw else {}

        try:
            return _send_once()
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            return exc.code, json.loads(raw) if raw else {}
        except urllib.error.URLError:
            # Local ephemeral CI/network race; retry once for deterministic tests.
            return _send_once()

    def _get_json(self, path):
        req = urllib.request.Request(f'{self.base}{path}', method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}

    def test_follow_start_requires_ui_origin(self):
        status, payload = self._post_json('/control/follow/start', {'target_id': 1}, with_origin=False)
        self.assertEqual(status, 403)
        self.assertEqual(payload.get('error'), 'forbidden')

    def test_follow_start_and_state(self):
        status, payload = self._post_json('/control/follow/start', {'target_id': 1})
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'started')

        status, state = self._get_json('/control/follow/state')
        self.assertEqual(status, 200)
        self.assertTrue(state.get('enabled'))
        self.assertEqual(state.get('target_id'), 1)

    def test_follow_observation_drives_autonomous_mode(self):
        self._post_json('/control/disarm')
        self._post_json('/control/estop/reset')
        self._post_json('/control/arm')
        self._post_json('/control/follow/start', {'target_id': 1})

        status, payload = self._post_json(
            '/control/follow/observation',
            {'target_id': 1, 'center_x': 0.75, 'area': 0.08},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'accepted')

        time.sleep(0.25)
        status, control = self._get_json('/control/state')
        self.assertEqual(status, 200)
        self.assertEqual(control.get('mode'), 'autonomous')
        self.assertEqual(control.get('active_behavior'), 'follow')

    def test_lost_target_handling_stops_motion(self):
        self._post_json('/control/disarm')
        self._post_json('/control/estop/reset')
        self._post_json('/control/arm')
        self._post_json('/control/follow/start', {'target_id': 1})
        self._post_json('/control/follow/observation', {'target_id': 1, 'center_x': 0.8, 'area': 0.05})

        time.sleep(0.25)
        status, active_state = self._get_json('/control/state')
        self.assertEqual(status, 200)
        self.assertGreater(abs(active_state.get('linear_mps', 0.0)), 0.0)

        # Wait longer than follow target timeout to trigger lost-target decay.
        time.sleep(1.1)
        status, follow_state = self._get_json('/control/follow/state')
        self.assertEqual(status, 200)
        self.assertTrue(follow_state.get('lost_target'))

        status, control_state = self._get_json('/control/state')
        self.assertEqual(status, 200)
        self.assertAlmostEqual(control_state.get('linear_mps', 0.0), 0.0, places=2)

    def test_estop_overrides_follow_and_disables_it(self):
        self._post_json('/control/disarm')
        self._post_json('/control/estop/reset')
        self._post_json('/control/arm')
        self._post_json('/control/follow/start', {'target_id': 1})
        self._post_json('/control/follow/observation', {'target_id': 1, 'center_x': 0.2, 'area': 0.06})
        time.sleep(0.2)

        status, _payload = self._post_json('/control/estop')
        self.assertEqual(status, 200)

        status, control = self._get_json('/control/state')
        self.assertEqual(status, 200)
        self.assertTrue(control.get('estop_latched'))
        self.assertAlmostEqual(control.get('linear_mps', 0.0), 0.0, places=3)
        self.assertAlmostEqual(control.get('angular_rps', 0.0), 0.0, places=3)

        status, follow = self._get_json('/control/follow/state')
        self.assertEqual(status, 200)
        self.assertFalse(follow.get('enabled'))


if __name__ == '__main__':
    unittest.main()
