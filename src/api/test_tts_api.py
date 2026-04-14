#!/usr/bin/env python3
"""Integration tests for TTS API endpoint."""

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


class _FakeTTSProvider:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def synthesize(self, text: str, *, voice: str) -> bytes:
        if self.should_fail:
            raise RuntimeError('provider failed')
        return b'ID3FAKE-MP3'


class TestTTSEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18086'
        os.environ['OPENAI_API_KEY'] = 'test-key-123'

        APIHandler._tts_provider = _FakeTTSProvider()

        cls.server = HTTPServer(('localhost', 18086), APIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)
        cls.base_url = 'http://localhost:18086'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)

    def _post_json(self, path, payload):
        req = urllib.request.Request(
            f'{self.base_url}{path}',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_tts_missing_text(self):
        status, _headers, _body = self._post_json('/voice/tts', {'voice': 'alloy'})
        self.assertEqual(status, 400)

    def test_tts_success_returns_audio(self):
        status, headers, body = self._post_json('/voice/tts', {'text': 'hello world'})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get('Content-Type'), 'audio/mpeg')
        self.assertGreater(len(body), 0)

    def test_tts_endpoint_exists_post_only(self):
        req = urllib.request.Request(f'{self.base_url}/voice/tts', method='GET')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
