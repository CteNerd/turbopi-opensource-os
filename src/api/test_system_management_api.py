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
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, None

    @patch('subprocess.run')
    def test_restart_returns_202(self, _mock_run):
        status, data = self._post('/system/restart')
        self.assertEqual(status, 202)
        self.assertEqual(data['status'], 'restart_initiated')

    @patch('subprocess.run')
    def test_restart_does_not_call_reboot(self, mock_run):
        self._post('/system/restart')
        time.sleep(0.2)  # allow background thread to run
        for call in mock_run.call_args_list:
            args = call[0][0] if call[0] else call[1].get('args', [])
            self.assertNotIn('reboot', args,
                             "Restart must not invoke system reboot")

    @patch('subprocess.run')
    def test_reboot_returns_202(self, _mock_run):
        status, data = self._post('/system/reboot')
        self.assertEqual(status, 202)
        self.assertEqual(data['status'], 'reboot_initiated')

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


if __name__ == '__main__':
    unittest.main()
