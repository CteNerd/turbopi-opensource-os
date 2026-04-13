#!/usr/bin/env python3
"""Integration and unit tests for observability/diagnostics endpoints."""

import json
import os
import sys
import tarfile
import threading
import time
import unittest
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler, redact_secrets


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
        with urllib.request.urlopen(f'{self.base}/diagnostics/bundle', timeout=10) as response:
            content_type = response.headers.get('Content-Type', '')
            body = response.read()

        self.assertEqual(content_type, 'application/gzip')
        bundle_path = os.path.join('/tmp', f'turbopi-diagnostics-{int(time.time())}.tar.gz')
        with open(bundle_path, 'wb') as handle:
            handle.write(body)

        with tarfile.open(bundle_path, 'r:gz') as archive:
            names = archive.getnames()
            self.assertIn('health.json', names)
            self.assertIn('config.env.redacted', names)
            self.assertIn('logs/systemd.log.redacted', names)


if __name__ == '__main__':
    unittest.main()
