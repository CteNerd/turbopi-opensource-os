#!/usr/bin/env python3
"""Integration tests for conversation API endpoint."""

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


class TestConversationAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18087'
        os.environ['UI_PORT'] = '8081'
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

        cls.server = HTTPServer(('localhost', 18087), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18087'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def _post_json(self, path, payload, with_origin=True):
        req = urllib.request.Request(
            f'{self.base}{path}',
            data=json.dumps(payload).encode('utf-8'),
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        if with_origin:
            req.add_header('Origin', 'http://localhost:8081')
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                raw = response.read().decode('utf-8')
                try:
                    return response.status, json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    return response.status, {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8')
            try:
                return exc.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return exc.code, {}

    def test_conversation_requires_ui_origin(self):
        status, payload = self._post_json('/voice/conversation', {'message': 'hello'}, with_origin=False)
        self.assertEqual(status, 403)
        self.assertEqual(payload.get('error'), 'forbidden')

    def test_conversation_replies_with_fallback_when_no_api_key(self):
        status, payload = self._post_json('/voice/conversation', {'message': 'how are you?'})
        self.assertEqual(status, 200)
        self.assertIn('reply', payload)
        self.assertFalse(payload.get('guardrail_triggered'))

    def test_conversation_guardrail_blocks_command_like_input(self):
        status, payload = self._post_json('/voice/conversation', {'message': 'please follow me'})
        self.assertEqual(status, 200)
        self.assertTrue(payload.get('guardrail_triggered'))
        self.assertIn('cannot process control commands', payload.get('reply', '').lower())

    def test_conversation_missing_message(self):
        status, _payload = self._post_json('/voice/conversation', {})
        self.assertEqual(status, 400)

    def test_conversation_message_too_long(self):
        status, _payload = self._post_json('/voice/conversation', {'message': 'x' * 1001})
        self.assertEqual(status, 400)

    def test_conversation_payload_too_large(self):
        status, _payload = self._post_json('/voice/conversation', {'message': 'x' * 20000})
        self.assertEqual(status, 413)


class TestConversationIsolation(unittest.TestCase):
    """Safety inspection test: conversation handler must not drive motors directly."""

    def test_conversation_handler_no_control_execution(self):
        import inspect

        source = inspect.getsource(APIHandler.handle_voice_conversation)

        forbidden_patterns = [
            '.arm(', '.disarm(', '.apply_drive(', '.apply_autonomy(',
            'get_control_arbiter(', '.engage_estop(', '.clear_estop(',
        ]

        for forbidden in forbidden_patterns:
            self.assertNotIn(forbidden, source, f"Conversation handler must not call {forbidden}")


if __name__ == '__main__':
    unittest.main()
