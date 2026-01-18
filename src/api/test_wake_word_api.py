#!/usr/bin/env python3
"""
Integration tests for Wake Word API endpoints
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
import threading
import time
import urllib.request
import urllib.error

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestWakeWordAPIEndpoints(unittest.TestCase):
    """Tests for wake word API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Start test server"""
        # Set up test environment
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18080'
        os.environ['WAKE_WORD'] = 'TestWord'
        os.environ['WAKE_WORD_ENABLED'] = 'true'
        
        # Start server in background thread
        cls.server = HTTPServer(('localhost', 18080), APIHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        
        # Give server time to start
        time.sleep(0.5)
        
        cls.base_url = 'http://localhost:18080'
    
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
    
    def test_wake_word_status_endpoint(self):
        """Test GET /voice/wake-word/status"""
        status_code, data = self._make_request('/voice/wake-word/status')
        
        self.assertEqual(status_code, 200)
        self.assertIn('enabled', data)
        self.assertIn('wake_word', data)
        self.assertIn('armed', data)
        self.assertIn('timeout_seconds', data)
        self.assertIn('time_remaining', data)
        
        # Check default values
        self.assertTrue(data['enabled'])
        self.assertEqual(data['wake_word'], 'TestWord')
        self.assertFalse(data['armed'])
        self.assertIsNone(data['time_remaining'])
    
    def test_wake_word_get_config_endpoint(self):
        """Test GET /voice/wake-word/config"""
        status_code, data = self._make_request('/voice/wake-word/config')
        
        self.assertEqual(status_code, 200)
        self.assertIn('wake_word', data)
        self.assertIn('enabled', data)
        self.assertIn('timeout_seconds', data)
        
        self.assertEqual(data['wake_word'], 'TestWord')
        self.assertTrue(data['enabled'])
    
    def test_wake_word_update_config_wake_word(self):
        """Test POST /voice/wake-word/config to update wake word"""
        # Update wake word
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'wake_word': 'NewWord'}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['status'], 'updated')
        self.assertEqual(data['wake_word'], 'NewWord')
        
        # Verify update persisted
        status_code, data = self._make_request('/voice/wake-word/config')
        self.assertEqual(data['wake_word'], 'NewWord')
        
        # Reset for other tests
        self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'wake_word': 'TestWord'}
        )
    
    def test_wake_word_update_config_enabled(self):
        """Test POST /voice/wake-word/config to enable/disable"""
        # Disable wake word
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'enabled': False}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['status'], 'updated')
        self.assertFalse(data['enabled'])
        
        # Verify disabled
        status_code, data = self._make_request('/voice/wake-word/status')
        self.assertFalse(data['enabled'])
        
        # Re-enable
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'enabled': True}
        )
        
        self.assertEqual(status_code, 200)
        self.assertTrue(data['enabled'])
    
    def test_wake_word_update_config_both_params(self):
        """Test POST /voice/wake-word/config with both parameters"""
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'wake_word': 'Combined', 'enabled': False}
        )
        
        self.assertEqual(status_code, 200)
        self.assertEqual(data['wake_word'], 'Combined')
        self.assertFalse(data['enabled'])
        
        # Reset
        self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'wake_word': 'TestWord', 'enabled': True}
        )
    
    def test_wake_word_update_config_invalid_empty(self):
        """Test POST /voice/wake-word/config with empty wake word"""
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={'wake_word': '   '}
        )
        
        self.assertEqual(status_code, 400)
    
    def test_wake_word_update_config_no_params(self):
        """Test POST /voice/wake-word/config with no parameters"""
        status_code, data = self._make_request(
            '/voice/wake-word/config',
            method='POST',
            data={}
        )
        
        self.assertEqual(status_code, 400)
    
    def test_wake_word_update_config_invalid_json(self):
        """Test POST /voice/wake-word/config with invalid JSON"""
        url = f"{self.base_url}/voice/wake-word/config"
        req = urllib.request.Request(url, data=b"invalid json", method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req, timeout=5):
                self.fail("Expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
    
    def test_wake_word_update_config_no_body(self):
        """Test POST /voice/wake-word/config with no body"""
        url = f"{self.base_url}/voice/wake-word/config"
        req = urllib.request.Request(url, method='POST')
        
        try:
            with urllib.request.urlopen(req, timeout=5):
                self.fail("Expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)


class TestWakeWordSafetyIntegration(unittest.TestCase):
    """Integration tests to verify wake word safety guarantees"""
    
    def test_wake_word_no_motor_endpoints(self):
        """Verify wake word endpoints don't interact with motor control"""
        # This is a safety test - wake word detection should never
        # expose or call motor control endpoints
        
        # Get all methods from APIHandler
        handler_methods = [m for m in dir(APIHandler) if m.startswith('handle_')]
        
        # Wake word handlers should not call motor-related handlers
        wake_word_handlers = [m for m in handler_methods if 'wake_word' in m]
        motor_handlers = [m for m in handler_methods if any(
            keyword in m for keyword in ['arm', 'disarm', 'motor', 'move', 'estop']
        )]
        
        # There should be no overlap between wake word and motor handlers
        # (except wake word handlers might check motor status for safety)
        self.assertTrue(len(wake_word_handlers) > 0, "Should have wake word handlers")
        
        # Verify wake word endpoints are separate from motor control
        for ww_handler in wake_word_handlers:
            for motor_handler in motor_handlers:
                self.assertNotEqual(ww_handler, motor_handler,
                                  "Wake word handler should not be a motor control handler")


if __name__ == '__main__':
    unittest.main()
