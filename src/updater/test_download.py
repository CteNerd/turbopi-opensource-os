#!/usr/bin/env python3
"""
Unit tests for download and verification module.
"""

import os
import tempfile
import unittest
import hashlib
from unittest.mock import patch, MagicMock
import urllib.error

from download import (
    download_file,
    calculate_sha256,
    verify_checksum,
    download_and_verify,
    redact_url,
    DownloadError,
    ChecksumError
)


class TestRedactUrl(unittest.TestCase):
    """Tests for URL redaction functionality"""
    
    def test_redact_url_with_credentials(self):
        """Test that credentials are removed from URLs"""
        url = "http://user:pass@host.com/path"
        result = redact_url(url)
        self.assertEqual(result, "http://host.com/path")
        self.assertNotIn("user", result)
        self.assertNotIn("pass", result)
    
    def test_redact_url_with_query_parameters(self):
        """Test that query parameters are removed"""
        url = "http://host.com/path?token=secret123&key=value"
        result = redact_url(url)
        self.assertEqual(result, "http://host.com/path")
        self.assertNotIn("token", result)
        self.assertNotIn("secret123", result)
    
    def test_redact_url_preserves_port(self):
        """Test that port numbers are preserved"""
        url = "http://host.com:8080/path"
        result = redact_url(url)
        self.assertEqual(result, "http://host.com:8080/path")
        self.assertIn(":8080", result)
    
    def test_redact_url_with_credentials_and_port(self):
        """Test that credentials are removed but port is preserved"""
        url = "https://myuser:mypass@api.github.com:443/download/v1.0.0/file.tar.gz"
        result = redact_url(url)
        self.assertEqual(result, "https://api.github.com:443/download/v1.0.0/file.tar.gz")
        self.assertNotIn("myuser", result)
        self.assertNotIn("mypass", result)
        self.assertIn(":443", result)
    
    def test_redact_url_with_everything(self):
        """Test URL with credentials, port, query params, and fragment"""
        url = "https://user:pass@host.com:9000/path?token=secret#section"
        result = redact_url(url)
        self.assertEqual(result, "https://host.com:9000/path")
        self.assertNotIn("user", result)
        self.assertNotIn("pass", result)
        self.assertNotIn("token", result)
        self.assertNotIn("secret", result)
        self.assertNotIn("#section", result)
        self.assertIn(":9000", result)
    
    def test_redact_url_public_url_unchanged(self):
        """Test that public URLs without credentials remain unchanged"""
        url = "https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz"
        result = redact_url(url)
        self.assertEqual(result, url)
    
    def test_redact_url_localhost_with_port(self):
        """Test localhost URLs with custom ports"""
        url = "http://localhost:8000/download"
        result = redact_url(url)
        self.assertEqual(result, "http://localhost:8000/download")
    
    def test_redact_url_invalid_returns_placeholder(self):
        """Test that invalid URLs return safe placeholder or handle gracefully"""
        # Some invalid URLs might be partially parsed, so we just ensure
        # no exception is raised and the function returns a string
        invalid_urls = ["not a url", "://missing-scheme", ""]
        for url in invalid_urls:
            result = redact_url(url)
            # Should return a string (either redacted or partially parsed)
            self.assertIsInstance(result, str)
            # For completely invalid URLs, should return placeholder
            if not url or url.startswith("://"):
                self.assertIn("redacted", result.lower())
    
    def test_redact_url_https_with_query(self):
        """Test HTTPS URLs with query parameters"""
        url = "https://api.example.com/repos/user/repo/tarball?access_token=ghp_secret123"
        result = redact_url(url)
        self.assertEqual(result, "https://api.example.com/repos/user/repo/tarball")
        self.assertNotIn("access_token", result)
        self.assertNotIn("ghp_secret123", result)


class TestCalculateSha256(unittest.TestCase):
    """Tests for SHA256 calculation"""
    
    def test_calculate_sha256_success(self):
        """Test successful checksum calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            # Calculate expected checksum
            expected = hashlib.sha256(b"test content").hexdigest()
            
            # Test function
            result = calculate_sha256(temp_path)
            self.assertEqual(result, expected)
        finally:
            os.unlink(temp_path)
    
    def test_calculate_sha256_large_file(self):
        """Test checksum calculation for large file (multiple chunks)"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            # Write more than 8192 bytes to test chunking
            content = b"x" * 20000
            f.write(content)
            temp_path = f.name
        
        try:
            # Calculate expected checksum
            expected = hashlib.sha256(content).hexdigest()
            
            # Test function
            result = calculate_sha256(temp_path)
            self.assertEqual(result, expected)
        finally:
            os.unlink(temp_path)
    
    def test_calculate_sha256_missing_file(self):
        """Test error handling for missing file"""
        with self.assertRaises(DownloadError):
            calculate_sha256("/nonexistent/file.txt")


class TestVerifyChecksum(unittest.TestCase):
    """Tests for checksum verification"""
    
    def test_verify_checksum_success(self):
        """Test successful checksum verification"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            expected = hashlib.sha256(b"test content").hexdigest()
            
            # Should not raise exception
            verify_checksum(temp_path, expected)
        finally:
            os.unlink(temp_path)
    
    def test_verify_checksum_with_prefix(self):
        """Test verification with sha256: prefix"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            expected = "sha256:" + hashlib.sha256(b"test content").hexdigest()
            
            # Should not raise exception
            verify_checksum(temp_path, expected)
        finally:
            os.unlink(temp_path)
    
    def test_verify_checksum_case_insensitive(self):
        """Test verification is case insensitive"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            expected = hashlib.sha256(b"test content").hexdigest().upper()
            
            # Should not raise exception
            verify_checksum(temp_path, expected)
        finally:
            os.unlink(temp_path)
    
    def test_verify_checksum_mismatch(self):
        """Test checksum mismatch raises ChecksumError"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            wrong_checksum = "0" * 64
            
            with self.assertRaises(ChecksumError) as cm:
                verify_checksum(temp_path, wrong_checksum)
            
            self.assertIn("Checksum mismatch", str(cm.exception))
        finally:
            os.unlink(temp_path)
    
    def test_verify_checksum_missing_file(self):
        """Test error handling for missing file"""
        with self.assertRaises(DownloadError):
            verify_checksum("/nonexistent/file.txt", "abc123")


class TestDownloadFile(unittest.TestCase):
    """Tests for file download"""
    
    @patch('urllib.request.urlopen')
    def test_download_file_success(self, mock_urlopen):
        """Test successful file download"""
        # Mock response
        mock_response = MagicMock()
        mock_response.headers.get.return_value = '12'
        mock_response.read.side_effect = [b"test content", b""]
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            download_file("http://example.com/file.txt", dest)
            
            # Verify file was created
            self.assertTrue(os.path.exists(dest))
            
            # Verify content
            with open(dest, 'rb') as f:
                self.assertEqual(f.read(), b"test content")
    
    @patch('urllib.request.urlopen')
    def test_download_file_creates_directory(self, mock_urlopen):
        """Test that download creates destination directory"""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = '4'
        mock_response.read.side_effect = [b"test", b""]
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "subdir", "test.txt")
            
            download_file("http://example.com/file.txt", dest)
            
            # Verify directory and file were created
            self.assertTrue(os.path.exists(dest))
    
    @patch('urllib.request.urlopen')
    def test_download_file_http_error(self, mock_urlopen):
        """Test HTTP error handling"""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com/file.txt",
            404,
            "Not Found",
            {},
            None
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            with self.assertRaises(DownloadError) as cm:
                download_file("http://example.com/file.txt", dest)
            
            self.assertIn("HTTP error", str(cm.exception))
            self.assertIn("404", str(cm.exception))
    
    @patch('urllib.request.urlopen')
    def test_download_file_network_error(self, mock_urlopen):
        """Test network error handling"""
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            with self.assertRaises(DownloadError) as cm:
                download_file("http://example.com/file.txt", dest)
            
            self.assertIn("Network error", str(cm.exception))


class TestDownloadAndVerify(unittest.TestCase):
    """Tests for combined download and verification"""
    
    @patch('download.download_file')
    @patch('download.verify_checksum')
    def test_download_and_verify_success(self, mock_verify, mock_download):
        """Test successful download and verification"""
        mock_download.return_value = None
        mock_verify.return_value = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            download_and_verify(
                "http://example.com/file.txt",
                dest,
                "abc123"
            )
            
            mock_download.assert_called_once()
            mock_verify.assert_called_once()
    
    @patch('download.download_file')
    @patch('download.verify_checksum')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_download_and_verify_checksum_failure_cleanup(
        self, mock_remove, mock_exists, mock_verify, mock_download
    ):
        """Test that invalid file is cleaned up on checksum failure"""
        mock_download.return_value = None
        mock_verify.side_effect = ChecksumError("Checksum mismatch")
        mock_exists.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            with self.assertRaises(ChecksumError):
                download_and_verify(
                    "http://example.com/file.txt",
                    dest,
                    "abc123"
                )
            
            # Verify cleanup was attempted
            mock_remove.assert_called_once_with(dest)
    
    @patch('download.download_file')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_download_and_verify_download_failure_cleanup(
        self, mock_remove, mock_exists, mock_download
    ):
        """Test that partial download is cleaned up on download failure"""
        mock_download.side_effect = DownloadError("Network error")
        mock_exists.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.txt")
            
            with self.assertRaises(DownloadError):
                download_and_verify(
                    "http://example.com/file.txt",
                    dest,
                    "abc123"
                )
            
            # Verify cleanup was attempted
            mock_remove.assert_called_once_with(dest)


class TestIntegration(unittest.TestCase):
    """Integration tests with real files"""
    
    def test_full_workflow(self):
        """Test complete download-verify workflow with real files"""
        # Create a test file with known content
        test_content = b"This is test content for integration testing."
        expected_checksum = hashlib.sha256(test_content).hexdigest()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source = os.path.join(tmpdir, "source.txt")
            with open(source, 'wb') as f:
                f.write(test_content)
            
            # Test checksum calculation
            calculated = calculate_sha256(source)
            self.assertEqual(calculated, expected_checksum)
            
            # Test verification success
            verify_checksum(source, expected_checksum)
            
            # Test verification failure
            wrong_checksum = "0" * 64
            with self.assertRaises(ChecksumError):
                verify_checksum(source, wrong_checksum)


if __name__ == '__main__':
    unittest.main()
