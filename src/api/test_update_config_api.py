#!/usr/bin/env python3
"""Integration tests for /updates/config endpoint."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestUpdateConfigAPI(unittest.TestCase):
    """Tests for update configuration API."""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls._config_path = os.path.join(cls._tmp_dir.name, 'config.env')
        with open(cls._config_path, 'w', encoding='utf-8') as handle:
            handle.write('ROBOT_NAME=TestBot\n')

        os.environ['API_HOST'] = 'localhost'
        os.environ['CONFIG_ENV_PATH'] = cls._config_path
        os.environ['AUTO_UPDATE'] = 'false'
        os.environ['AUTO_UPDATE_CHANNEL'] = 'stable'
        os.environ['AUTO_UPDATE_SCHEDULE_UTC'] = '03:00'

        cls.server = HTTPServer(('localhost', 0), APIHandler)
        assigned_port = cls.server.server_address[1]
        os.environ['API_PORT'] = str(assigned_port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)
        cls.base_url = f'http://localhost:{assigned_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        cls._tmp_dir.cleanup()

    def _make_request(self, path, method='GET', data=None, origin=None):
        url = f"{self.base_url}{path}"
        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')

        request = urllib.request.Request(url, data=body, method=method)
        if body is not None:
            request.add_header('Content-Type', 'application/json')
        if origin:
            request.add_header('Origin', origin)

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                payload = response.read().decode('utf-8')
                return response.status, json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode('utf-8')
            try:
                return exc.code, json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                return exc.code, {}

    def test_get_update_config_defaults(self):
        status, data = self._make_request('/updates/config')
        self.assertEqual(status, 200)
        self.assertFalse(data['auto_update'])
        self.assertEqual(data['channel'], 'stable')
        self.assertEqual(data['schedule_utc'], '03:00')

    def test_post_update_config_requires_origin(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data={'auto_update': True},
        )
        self.assertEqual(status, 403)
        self.assertEqual(data.get('error'), 'forbidden')

    def test_post_update_config_success_and_persistence(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data={
                'auto_update': True,
                'channel': 'stable',
                'schedule_utc': '02:15',
            },
            origin='http://localhost:8081',
        )
        self.assertEqual(status, 200)
        self.assertTrue(data['auto_update'])
        self.assertEqual(data['channel'], 'stable')
        self.assertEqual(data['schedule_utc'], '02:15')
        self.assertTrue(data['persisted'])

        with open(self.__class__._config_path, 'r', encoding='utf-8') as handle:
            content = handle.read()

        self.assertIn('AUTO_UPDATE=true', content)
        self.assertIn('AUTO_UPDATE_CHANNEL=stable', content)
        self.assertIn('AUTO_UPDATE_SCHEDULE_UTC=02:15', content)

    def test_post_update_config_rejects_non_stable_channel(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data={'channel': 'beta'},
            origin='http://localhost:8081',
        )
        self.assertEqual(status, 400)
        self.assertEqual(data.get('error'), 'bad_request')

    def test_post_update_config_rejects_invalid_schedule(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data={'schedule_utc': '24:00'},
            origin='http://localhost:8081',
        )
        self.assertEqual(status, 400)
        self.assertEqual(data.get('error'), 'bad_request')

    def test_post_update_config_rejects_non_object_json(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data=['not-an-object'],
            origin='http://localhost:8081',
        )
        self.assertEqual(status, 400)
        self.assertEqual(data.get('error'), 'bad_request')

    def test_post_update_config_rejects_payload_too_large(self):
        status, data = self._make_request(
            '/updates/config',
            method='POST',
            data={'schedule_utc': '03:00', 'padding': 'x' * 6000},
            origin='http://localhost:8081',
        )
        self.assertEqual(status, 413)
        self.assertEqual(data.get('error'), 'payload_too_large')

    def test_post_update_config_returns_500_when_persistence_fails(self):
        with patch('main.persist_update_config', return_value=False):
            status, data = self._make_request(
                '/updates/config',
                method='POST',
                data={'auto_update': True},
                origin='http://localhost:8081',
            )

        self.assertEqual(status, 500)
        self.assertEqual(data.get('error'), 'persistence_failed')
        self.assertFalse(data.get('persisted'))

    def test_post_update_config_persists_when_directory_is_not_writable(self):
        restricted_dir = tempfile.mkdtemp(dir=self.__class__._tmp_dir.name)
        restricted_config = os.path.join(restricted_dir, 'config.env')
        with open(restricted_config, 'w', encoding='utf-8') as handle:
            handle.write('AUTO_UPDATE=false\nAUTO_UPDATE_CHANNEL=stable\nAUTO_UPDATE_SCHEDULE_UTC=03:00\n')

        # Simulate hardened /etc directory: file is writable, directory is not.
        os.chmod(restricted_config, 0o660)
        os.chmod(restricted_dir, 0o550)

        previous_path = os.environ.get('CONFIG_ENV_PATH')
        os.environ['CONFIG_ENV_PATH'] = restricted_config
        try:
            status, data = self._make_request(
                '/updates/config',
                method='POST',
                data={'schedule_utc': '04:45'},
                origin='http://localhost:8081',
            )
            self.assertEqual(status, 200)
            self.assertTrue(data.get('persisted'))

            with open(restricted_config, 'r', encoding='utf-8') as handle:
                content = handle.read()
            self.assertIn('AUTO_UPDATE_SCHEDULE_UTC=04:45', content)
        finally:
            if previous_path is None:
                os.environ.pop('CONFIG_ENV_PATH', None)
            else:
                os.environ['CONFIG_ENV_PATH'] = previous_path
            os.chmod(restricted_dir, 0o750)


if __name__ == '__main__':
    unittest.main()
