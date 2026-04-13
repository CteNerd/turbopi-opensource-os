#!/usr/bin/env python3
"""
Tests for system management API endpoints:
  GET  /system/version
  POST /system/restart
  POST /system/reboot

These endpoints support Epic #16 (Update Management UI).
"""

import os
import sys
import json
import time
import unittest
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestSystemVersionEndpoint(unittest.TestCase):
    """Tests for GET /system/version"""

    @classmethod
    def setUpClass(cls):
        os.environ['API_PORT'] = '18082'
        os.environ['VERSION'] = '1.2.3'
        cls.server = HTTPServer(('localhost', 18082), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18082'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _get(self, path):
        with urllib.request.urlopen(f'{self.base}{path}', timeout=5) as r:
            return r.status, json.loads(r.read().decode())

    @patch('main.fetch_latest_stable_release', return_value={'version': '2.0.0', 'url': 'http://x', 'checksum': None})
    def test_version_returns_current_and_latest(self, _mock):
        status, data = self._get('/system/version')
        self.assertEqual(status, 200)
        self.assertEqual(data['current'], '1.2.3')
        self.assertEqual(data['latest_stable'], '2.0.0')

    @patch('main.fetch_latest_stable_release', return_value=None)
    def test_version_latest_stable_null_when_unavailable(self, _mock):
        status, data = self._get('/system/version')
        self.assertEqual(status, 200)
        self.assertEqual(data['current'], '1.2.3')
        self.assertIsNone(data['latest_stable'])


class TestSystemRestartRebootEndpoints(unittest.TestCase):
    """Tests for POST /system/restart and POST /system/reboot"""

    @classmethod
    def setUpClass(cls):
        os.environ['API_PORT'] = '18083'
        os.environ['VERSION'] = '0.1.0'
        cls.server = HTTPServer(('localhost', 18083), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18083'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _post(self, path):
        req = urllib.request.Request(f'{self.base}{path}', data=b'', method='POST')
        req.add_header('Origin', 'http://localhost:8081')
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                body = r.read().decode()
                return r.status, json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            return e.code, json.loads(error_body) if error_body else None

    def _wait_for_mock_call(self, mock_run, timeout=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if mock_run.called:
                return
            time.sleep(0.01)
        self.fail('Timed out waiting for background command execution')

    @patch('main.SYSTEM_ACTION_DELAY_SECONDS', 0)
    @patch('main.subprocess.run')
    def test_restart_returns_202(self, _mock_run):
        status, data = self._post('/system/restart')
        self.assertEqual(status, 202)
        self.assertIsNone(data)

    @patch('main.SYSTEM_ACTION_DELAY_SECONDS', 0)
    @patch('main.subprocess.run')
    def test_restart_uses_try_restart(self, mock_run):
        self._post('/system/restart')
        self._wait_for_mock_call(mock_run)
        command = mock_run.call_args[0][0]
        self.assertEqual(command[0:2], ['systemctl', 'try-restart'])
        self.assertNotIn('reboot', command)

    @patch('main.SYSTEM_ACTION_DELAY_SECONDS', 0)
    @patch('main.subprocess.run')
    def test_reboot_returns_202(self, _mock_run):
        status, data = self._post('/system/reboot')
        self.assertEqual(status, 202)
        self.assertIsNone(data)

    @patch('main.SYSTEM_ACTION_DELAY_SECONDS', 0)
    @patch('main.subprocess.run')
    def test_reboot_invokes_reboot_command(self, mock_run):
        self._post('/system/reboot')
        self._wait_for_mock_call(mock_run)
        self.assertEqual(mock_run.call_args[0][0], ['reboot'])

    def test_restart_not_accessible_via_get(self):
        try:
            urllib.request.urlopen(f'{self.base}/system/restart', timeout=5)
            self.fail("Expected 404 or 405")
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (404, 405))

    def test_reboot_not_accessible_via_get(self):
        try:
            urllib.request.urlopen(f'{self.base}/system/reboot', timeout=5)
            self.fail("Expected 404 or 405")
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (404, 405))

    def test_restart_requires_ui_origin(self):
        req = urllib.request.Request(f'{self.base}/system/restart', data=b'', method='POST')
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail('Expected 403')
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)
            body = json.loads(e.read().decode())
            self.assertEqual(body['error'], 'forbidden')

    def test_reboot_requires_ui_origin(self):
        req = urllib.request.Request(f'{self.base}/system/reboot', data=b'', method='POST')
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail('Expected 403')
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)
            body = json.loads(e.read().decode())
            self.assertEqual(body['error'], 'forbidden')


if __name__ == '__main__':
    unittest.main()
