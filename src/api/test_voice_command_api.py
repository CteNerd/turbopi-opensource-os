#!/usr/bin/env python3
"""
Integration tests for Voice Command API endpoint
"""

import os
import sys
import json
import unittest
from http.server import HTTPServer
import threading
import time
import urllib.request
import urllib.error

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestVoiceCommandAPIEndpoint(unittest.TestCase):
    """Tests for /voice/command endpoint"""
    
    @classmethod
    def setUpClass(cls):
        """Start test server"""
        # Set up test environment
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18082'
        os.environ['WAKE_WORD'] = 'TestWord'
        os.environ['WAKE_WORD_ENABLED'] = 'true'
        
        # Start server in background thread
        cls.server = HTTPServer(('localhost', 18082), APIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        
        # Give server time to start
        time.sleep(0.5)
        
        cls.base_url = 'http://localhost:18082'
    
    @classmethod
    def tearDownClass(cls):
        """Stop test server"""
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
    
    def _make_request(self, path, method='GET', data=None):
        """Helper to make HTTP requests"""
        url = f"{self.base_url}{path}"
        
        if data is not None:
            data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read().decode('utf-8')
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            return e.code, None
        except Exception as e:
            self.fail(f"Request failed: {e}")
    
    def test_voice_command_stop(self):
        """Test parsing STOP command"""
        status_code, data = self._make_request(
            '/voice/command',
            method='POST',
            data={'transcript': 'emergency stop'}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['command'], 'STOP')
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['confidence'], 1.0)
        self.assertIsNone(data['target'])
        self.assertEqual(data['raw_transcript'], 'emergency stop')
    
    def test_voice_command_follow(self):
        """Test parsing FOLLOW command"""
        status_code, data = self._make_request(
            '/voice/command',
            method='POST',
            data={'transcript': 'follow the person'}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['command'], 'FOLLOW')
        self.assertTrue(data['is_valid'])
        self.assertEqual(data['target'], 'person')
        self.assertGreater(data['confidence'], 0.0)
        self.assertEqual(data['raw_transcript'], 'follow the person')
    
    def test_voice_command_unknown(self):
        """Test parsing unknown command"""
        status_code, data = self._make_request(
            '/voice/command',
            method='POST',
            data={'transcript': 'turn on the lights'}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['command'], 'UNKNOWN')
        self.assertFalse(data['is_valid'])
        self.assertEqual(data['confidence'], 0.0)
        self.assertEqual(data['raw_transcript'], 'turn on the lights')
    
    def test_voice_command_missing_transcript(self):
        """Test error handling for missing transcript"""
        status_code, data = self._make_request(
            '/voice/command',
            method='POST',
            data={}
        )
        
        self.assertEqual(status_code, 400)
    
    def test_voice_command_no_body(self):
        """Test error handling for missing body"""
        url = f"{self.base_url}/voice/command"
        req = urllib.request.Request(url, method='POST')
        
        try:
            with urllib.request.urlopen(req, timeout=5):
                self.fail("Expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
    
    def test_voice_command_invalid_json(self):
        """Test error handling for invalid JSON"""
        url = f"{self.base_url}/voice/command"
        req = urllib.request.Request(url, data=b"invalid json", method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=5):
                self.fail("Expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)


class TestVoiceCommandSafety(unittest.TestCase):
    """Safety tests for voice command endpoint"""
    
    def test_voice_command_no_execution(self):
        """
        Verify voice command endpoint only parses, does not execute.
        
        This is a critical safety test - the endpoint should only return
        the parsed intent, not execute any robot actions.
        """
        # This test verifies by inspection that handle_voice_command
        # only calls parser.parse() and returns the result, without
        # calling any motor control or execution methods
        
        from main import APIHandler
        import inspect
        
        # Get the source code of handle_voice_command
        source = inspect.getsource(APIHandler.handle_voice_command)
        
        # Remove comments and docstrings to avoid false positives
        lines = []
        in_docstring = False
        for line in source.split('\n'):
            stripped = line.strip()
            # Skip docstrings
            if '"""' in stripped:
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            # Skip comments
            if stripped.startswith('#'):
                continue
            lines.append(line)
        
        source_no_comments = '\n'.join(lines)
        
        # Verify it doesn't call motor-related methods
        forbidden_patterns = [
            '.arm(', '.disarm(', '.move(', '.execute_command(',
            'motor.', 'control.execute'
        ]
        
        for forbidden in forbidden_patterns:
            self.assertNotIn(forbidden, source_no_comments.lower(),
                           f"Voice command handler should not call '{forbidden}'")
        
        # Verify it does call parser.parse()
        self.assertIn('parser.parse', source,
                     "Voice command handler should call parser.parse()")


if __name__ == '__main__':
    unittest.main()
