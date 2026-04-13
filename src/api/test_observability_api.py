#!/usr/bin/env python3
"""Integration and unit tests for observability/diagnostics endpoints."""

import json
import os
import sys
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler, build_diagnostics_bundle, redact_secrets


class TestObservabilityHelpers(unittest.TestCase):
    """Tests for secret redaction helper logic."""

    def test_redact_secrets_masks_known_patterns(self):
        raw = (
            'OPENAI_API_KEY=sk-secret\n'
            'password=my-pass\n'
            'Authorization: Bearer abc123\n'
            '{"api_key":"value","token":"value2"}\n'
        )
        redacted = redact_secrets(raw)
        self.assertNotIn('sk-secret', redacted)
        self.assertNotIn('my-pass', redacted)
        self.assertNotIn('abc123', redacted)
        self.assertIn('***REDACTED***', redacted)

    @patch('main._safe_run', return_value='Authorization: Bearer topsecret-token')
    def test_diagnostics_bundle_redacts_sensitive_material(self, _mock_safe_run):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, 'config.env')
            with open(config_path, 'w', encoding='utf-8') as handle:
                handle.write('OPENAI_API_KEY=sk-live-secret\npassword=plain-pass\n')

            with patch.dict(os.environ, {'DIAGNOSTICS_CONFIG_PATH': config_path}, clear=False):
                bundle = build_diagnostics_bundle()

            archive_path = os.path.join(tmp_dir, 'bundle.tar.gz')
            with open(archive_path, 'wb') as handle:
                handle.write(bundle)

            with tarfile.open(archive_path, 'r:gz') as archive:
                config_text = archive.extractfile('config.env.redacted').read().decode('utf-8')
                logs_text = archive.extractfile('logs/systemd.log.redacted').read().decode('utf-8')

            self.assertNotIn('sk-live-secret', config_text)
            self.assertNotIn('plain-pass', config_text)
            self.assertNotIn('topsecret-token', logs_text)
            self.assertIn('***REDACTED***', config_text)
            self.assertIn('***REDACTED***', logs_text)


class TestObservabilityAPI(unittest.TestCase):
    """Integration tests for expanded health and diagnostics bundle download."""

    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18086'
        cls.server = HTTPServer(('localhost', 18086), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18086'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def test_health_includes_expanded_fields(self):
        with urllib.request.urlopen(f'{self.base}/health', timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))

        self.assertIn('memory', payload)
        self.assertIn('disk', payload)
        self.assertIn('services', payload)
        self.assertIn('api', payload['services'])

    def test_diagnostics_bundle_is_downloadable_tar_gz(self):
        req = urllib.request.Request(f'{self.base}/diagnostics/bundle', method='GET')
        req.add_header('Origin', 'http://localhost:8081')
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            body = response.read()

        self.assertEqual(content_type, 'application/gzip')
        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as handle:
            handle.write(body)
            handle.flush()

            with tarfile.open(handle.name, 'r:gz') as archive:
                names = archive.getnames()
                self.assertIn('health.json', names)
                self.assertIn('config.env.redacted', names)
                self.assertIn('logs/systemd.log.redacted', names)

    def test_diagnostics_bundle_requires_ui_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(f'{self.base}/diagnostics/bundle', timeout=10)

        self.assertEqual(context.exception.code, 403)

    @patch('main.build_diagnostics_bundle', side_effect=RuntimeError('boom'))
    def test_diagnostics_bundle_500_returns_json_payload(self, _mock_bundle):
        req = urllib.request.Request(f'{self.base}/diagnostics/bundle', method='GET')
        req.add_header('Origin', 'http://localhost:8081')

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(req, timeout=10)

        self.assertEqual(context.exception.code, 500)
        self.assertEqual(context.exception.headers.get('Content-Type'), 'application/json')
        payload = json.loads(context.exception.read().decode('utf-8'))
        self.assertEqual(payload.get('error'), 'internal_server_error')
        self.assertEqual(payload.get('message'), 'Unable to generate diagnostics bundle')


if __name__ == '__main__':
    unittest.main()
