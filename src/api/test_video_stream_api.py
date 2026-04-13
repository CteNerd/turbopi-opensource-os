#!/usr/bin/env python3
"""Integration tests for MJPEG video streaming endpoint."""

import os
import sys
import threading
import time
import unittest
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(__file__))

from main import APIHandler


class TestVideoStreamAPI(unittest.TestCase):
    """Tests video streaming response contract."""

    @classmethod
    def setUpClass(cls):
        os.environ['API_HOST'] = 'localhost'
        os.environ['API_PORT'] = '18085'
        cls.server = HTTPServer(('localhost', 18085), APIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.base = 'http://localhost:18085'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)

    def test_video_stream_content_type_and_frame_boundary(self):
        with urllib.request.urlopen(f'{self.base}/video/stream?frames=1', timeout=5) as response:
            content_type = response.headers.get('Content-Type', '')
            body = response.read()

        self.assertIn('multipart/x-mixed-replace', content_type)
        self.assertIn(b'--frame', body)
        self.assertIn(b'Content-Type: image/jpeg', body)


if __name__ == '__main__':
    unittest.main()
