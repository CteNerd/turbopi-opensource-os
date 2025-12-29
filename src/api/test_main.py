#!/usr/bin/env python3
"""
Unit tests for TurboPi API Backend Service.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import (
    get_current_version,
    normalize_version,
    is_newer_version,
    fetch_latest_stable_release,
)


class TestGetCurrentVersion(unittest.TestCase):
    """Tests for get_current_version function"""
    
    def test_get_version_from_env(self):
        """Test that version is read from VERSION environment variable"""
        with patch.dict(os.environ, {'VERSION': '1.2.3'}):
            result = get_current_version()
            self.assertEqual(result, '1.2.3')
    
    def test_get_version_default(self):
        """Test default version when VERSION env var is not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_current_version()
            self.assertEqual(result, '0.1.0-dev')
    
    def test_get_version_with_dev_suffix(self):
        """Test version with -dev suffix"""
        with patch.dict(os.environ, {'VERSION': '0.2.0-dev'}):
            result = get_current_version()
            self.assertEqual(result, '0.2.0-dev')


class TestNormalizeVersion(unittest.TestCase):
    """Tests for normalize_version function"""
    
    def test_normalize_standard_version(self):
        """Test normalizing a standard semantic version"""
        result = normalize_version('1.2.3')
        self.assertEqual(result, (1, 2, 3))
    
    def test_normalize_version_with_v_prefix(self):
        """Test normalizing version with 'v' prefix"""
        result = normalize_version('v1.2.3')
        self.assertEqual(result, (1, 2, 3))
    
    def test_normalize_version_with_dev_suffix(self):
        """Test normalizing version with -dev suffix"""
        result = normalize_version('1.2.3-dev')
        self.assertEqual(result, (1, 2, 3))
    
    def test_normalize_version_with_alpha_suffix(self):
        """Test normalizing version with -alpha suffix"""
        result = normalize_version('2.0.0-alpha')
        self.assertEqual(result, (2, 0, 0))
    
    def test_normalize_short_version(self):
        """Test normalizing short version (e.g., '1.2')"""
        result = normalize_version('1.2')
        self.assertEqual(result, (1, 2, 0))
    
    def test_normalize_single_digit_version(self):
        """Test normalizing single digit version"""
        result = normalize_version('1')
        self.assertEqual(result, (1, 0, 0))
    
    def test_normalize_invalid_version(self):
        """Test normalizing invalid version string"""
        result = normalize_version('invalid')
        self.assertEqual(result, (0, 0, 0))
    
    def test_normalize_empty_version(self):
        """Test normalizing empty version string"""
        result = normalize_version('')
        self.assertEqual(result, (0, 0, 0))


class TestIsNewerVersion(unittest.TestCase):
    """Tests for is_newer_version function"""
    
    def test_newer_version_major(self):
        """Test that newer major version is detected"""
        self.assertTrue(is_newer_version('1.0.0', '2.0.0'))
    
    def test_newer_version_minor(self):
        """Test that newer minor version is detected"""
        self.assertTrue(is_newer_version('1.1.0', '1.2.0'))
    
    def test_newer_version_patch(self):
        """Test that newer patch version is detected"""
        self.assertTrue(is_newer_version('1.0.1', '1.0.2'))
    
    def test_same_version(self):
        """Test that same version is not detected as newer"""
        self.assertFalse(is_newer_version('1.0.0', '1.0.0'))
    
    def test_older_version(self):
        """Test that older version is not detected as newer"""
        self.assertFalse(is_newer_version('2.0.0', '1.0.0'))
    
    def test_dev_version_comparison(self):
        """Test comparison with -dev suffix"""
        # 1.0.1 (stable) is newer than 1.0.0-dev
        self.assertTrue(is_newer_version('1.0.0-dev', '1.0.1'))
        # 1.0.0-dev and 1.0.0 are considered equal (both normalize to 1.0.0)
        self.assertFalse(is_newer_version('1.0.0-dev', '1.0.0'))
    
    def test_v_prefix_comparison(self):
        """Test comparison with 'v' prefix"""
        self.assertTrue(is_newer_version('v1.0.0', 'v1.0.1'))


class TestFetchLatestStableRelease(unittest.TestCase):
    """Tests for fetch_latest_stable_release function"""
    
    @patch('urllib.request.urlopen')
    def test_fetch_success_with_assets(self, mock_urlopen):
        """Test successful fetch with tar.gz asset"""
        # Mock response data
        mock_response_data = {
            'tag_name': 'v1.2.3',
            'assets': [
                {
                    'name': 'turbopi-1.2.3.tar.gz',
                    'browser_download_url': 'https://github.com/example/turbopi-1.2.3.tar.gz'
                }
            ]
        }
        
        # Mock urlopen context manager
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = fetch_latest_stable_release()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['url'], 'https://github.com/example/turbopi-1.2.3.tar.gz')
    
    @patch('urllib.request.urlopen')
    def test_fetch_success_without_assets(self, mock_urlopen):
        """Test successful fetch without assets (uses tarball_url fallback)"""
        mock_response_data = {
            'tag_name': 'v1.2.3',
            'assets': [],
            'tarball_url': 'https://api.github.com/repos/example/tarball/v1.2.3'
        }
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = fetch_latest_stable_release()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['url'], 'https://api.github.com/repos/example/tarball/v1.2.3')
    
    @patch('urllib.request.urlopen')
    def test_fetch_http_error(self, mock_urlopen):
        """Test handling of HTTP error"""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            'url', 404, 'Not Found', {}, None
        )
        
        result = fetch_latest_stable_release()
        
        self.assertIsNone(result)
    
    @patch('urllib.request.urlopen')
    def test_fetch_network_error(self, mock_urlopen):
        """Test handling of network error"""
        mock_urlopen.side_effect = urllib.error.URLError('Connection failed')
        
        result = fetch_latest_stable_release()
        
        self.assertIsNone(result)
    
    @patch('urllib.request.urlopen')
    def test_fetch_invalid_json(self, mock_urlopen):
        """Test handling of invalid JSON response"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'invalid json'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = fetch_latest_stable_release()
        
        self.assertIsNone(result)
    
    @patch('urllib.request.urlopen')
    def test_fetch_missing_fields(self, mock_urlopen):
        """Test handling of response with missing fields"""
        mock_response_data = {}  # Missing tag_name
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = fetch_latest_stable_release()
        
        # Should return None when essential field tag_name is missing
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
