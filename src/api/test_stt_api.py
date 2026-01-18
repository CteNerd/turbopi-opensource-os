#!/usr/bin/env python3
"""
Unit tests for STT API endpoint

These tests validate the basic structure and error handling of the STT endpoint.
Full integration tests with real OpenAI API calls would be done separately.
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


class TestSTTEndpoint(unittest.TestCase):
    """Tests for /voice/stt endpoint"""
    
    @classmethod
    def setUpClass(cls):
        """Start test server"""
        # Set up test environment
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18082'
        os.environ['OPENAI_API_KEY'] = 'test-key-123'
        
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
    
    def _make_request(self, path, method='GET', data=None, headers=None):
        """Helper to make HTTP requests"""
        url = f"{self.base_url}{path}"
        
        req = urllib.request.Request(url, data=data, method=method)
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                body = response.read().decode('utf-8')
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            return e.code, None
        except Exception as e:
            return None, str(e)
    
    def test_stt_missing_api_key(self):
        """Test STT request without API key configured"""
        # Save original state
        original_key_exists = 'OPENAI_API_KEY' in os.environ
        original_key = os.environ.get('OPENAI_API_KEY')
        
        # Temporarily remove API key
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        try:
            audio_data = b'RIFF....WAVE....' + b'\x00' * 100
            status_code, _ = self._make_request('/voice/stt', 'POST', audio_data, 
                                                 {'Content-Type': 'audio/wav'})
            
            self.assertEqual(status_code, 500)
        finally:
            # Restore original state precisely
            if original_key_exists:
                os.environ['OPENAI_API_KEY'] = original_key
            elif 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
    
    def test_stt_wrong_content_type(self):
        """Test STT request with wrong Content-Type"""
        audio_data = b'some data'
        status_code, _ = self._make_request('/voice/stt', 'POST', audio_data,
                                             {'Content-Type': 'application/json'})
        
        self.assertEqual(status_code, 400)
    
    def test_stt_empty_body(self):
        """Test STT request with empty body"""
        status_code, _ = self._make_request('/voice/stt', 'POST', b'',
                                             {'Content-Type': 'audio/wav'})
        
        self.assertEqual(status_code, 400)
    
    def test_stt_endpoint_exists(self):
        """Test that the /voice/stt endpoint exists and requires POST"""
        # GET should return 404 (not found)
        status_code, _ = self._make_request('/voice/stt', 'GET')
        self.assertEqual(status_code, 404)
    
    def test_stt_invalid_content_length(self):
        """Test STT request with invalid Content-Length header"""
        # Test with non-numeric Content-Length
        url = f"{self.base_url}/voice/stt"
        
        # Create a custom request with invalid Content-Length
        import http.client
        conn = http.client.HTTPConnection('localhost', 18082)
        try:
            # Send headers manually
            conn.putrequest('POST', '/voice/stt')
            conn.putheader('Content-Type', 'audio/wav')
            conn.putheader('Content-Length', 'invalid')  # Invalid value
            conn.endheaders()
            
            response = conn.getresponse()
            self.assertEqual(response.status, 400)
        finally:
            conn.close()


if __name__ == '__main__':
    unittest.main()
