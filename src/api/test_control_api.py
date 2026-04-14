#!/usr/bin/env python3
"""Integration tests for control arm/disarm/estop endpoints."""

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


class TestControlAPI(unittest.TestCase):
    """Tests for control safety endpoints."""

    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18084'
        cls.server = HTTPServer(('localhost', 18084), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18084'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _post(self, path):
        req = urllib.request.Request(f'{self.base}{path}', data=b'', method='POST')
        req.add_header('Origin', 'http://localhost:8081')
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read().decode()
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            return exc.code, json.loads(body) if body else {}

    def _post_no_origin(self, path):
        req = urllib.request.Request(f'{self.base}{path}', data=b'', method='POST')
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read().decode()
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            return exc.code, json.loads(body) if body else {}

    def _get(self, path):
        req = urllib.request.Request(f'{self.base}{path}', method='GET')
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body else {}

    def test_arm_endpoint(self):
        status, payload = self._post('/control/arm')
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'armed')

    def test_disarm_endpoint(self):
        self._post('/control/arm')
        status, payload = self._post('/control/disarm')
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'disarmed')

    def test_estop_endpoint_latches(self):
        status, payload = self._post('/control/estop')
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'estop_engaged')

        status, payload = self._post('/control/arm')
        self.assertEqual(status, 409)
        self.assertEqual(payload.get('status'), 'blocked')

    def test_estop_reset_allows_rearm(self):
        self._post('/control/estop')
        status, payload = self._post('/control/estop/reset')
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'estop_cleared')

        status, payload = self._post('/control/arm')
        self.assertEqual(status, 200)
        self.assertEqual(payload.get('status'), 'armed')

    def test_control_state_endpoint(self):
        self._post('/control/disarm')
        status, payload = self._get('/control/state')
        self.assertEqual(status, 200)
        self.assertIn('armed', payload)
        self.assertIn('estop_latched', payload)
        self.assertIn('deadman_triggered', payload)
        self.assertIn('motor_backend', payload)
        self.assertIn('motor_disabled_channels', payload)
        self.assertIn('motor_degraded', payload)

    def test_control_post_requires_ui_origin(self):
        status, payload = self._post_no_origin('/control/arm')
        self.assertEqual(status, 403)
        self.assertEqual(payload.get('error'), 'forbidden')


if __name__ == '__main__':
    unittest.main()