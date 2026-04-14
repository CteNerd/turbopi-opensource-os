#!/usr/bin/env python3
"""
Integration tests for updater service with download functionality.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from main import UpdaterService
from download import DownloadError, ChecksumError


class TestUpdaterServiceDownload(unittest.TestCase):
    """Tests for updater service download integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Save original environment variables
        self.original_env = {
            'ROBOT_NAME': os.environ.get('ROBOT_NAME'),
            'AUTO_UPDATE': os.environ.get('AUTO_UPDATE'),
            'AUTO_UPDATE_CHANNEL': os.environ.get('AUTO_UPDATE_CHANNEL'),
            'AUTO_UPDATE_SCHEDULE_UTC': os.environ.get('AUTO_UPDATE_SCHEDULE_UTC'),
            'DOWNLOAD_DIR': os.environ.get('DOWNLOAD_DIR'),
            'LOG_LEVEL': os.environ.get('LOG_LEVEL')
        }
        
        # Set environment variables
        os.environ['ROBOT_NAME'] = 'TestBot'
        os.environ['AUTO_UPDATE'] = 'false'
        os.environ['AUTO_UPDATE_CHANNEL'] = 'stable'
        os.environ['AUTO_UPDATE_SCHEDULE_UTC'] = '03:00'
        os.environ['DOWNLOAD_DIR'] = self.temp_dir
        os.environ['LOG_LEVEL'] = 'INFO'
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    @patch('main.download_and_verify')
    def test_download_update_success(self, mock_download_verify):
        """Test successful update download"""
        mock_download_verify.return_value = None
        
        service = UpdaterService()
        
        result = service.download_update(
            url="http://example.com/turbopi-0.1.0.tar.gz",
            version="0.1.0",
            expected_checksum="abc123"
        )
        
        self.assertTrue(result)
        mock_download_verify.assert_called_once()
    
    @patch('main.download_and_verify')
    def test_download_update_checksum_failure(self, mock_download_verify):
        """Test that checksum failure is handled correctly"""
        mock_download_verify.side_effect = ChecksumError("Checksum mismatch")
        
        service = UpdaterService()
        
        result = service.download_update(
            url="http://example.com/turbopi-0.1.0.tar.gz",
            version="0.1.0",
            expected_checksum="abc123"
        )
        
        self.assertFalse(result)
    
    @patch('main.download_and_verify')
    def test_download_update_download_failure(self, mock_download_verify):
        """Test that download failure is handled correctly"""
        mock_download_verify.side_effect = DownloadError("Network error")
        
        service = UpdaterService()
        
        result = service.download_update(
            url="http://example.com/turbopi-0.1.0.tar.gz",
            version="0.1.0",
            expected_checksum="abc123"
        )
        
        self.assertFalse(result)
    
    @patch('main.download_and_verify')
    def test_download_update_creates_version_directory(self, mock_download_verify):
        """Test that version-specific directory is created"""
        mock_download_verify.return_value = None
        
        service = UpdaterService()
        
        service.download_update(
            url="http://example.com/turbopi-0.1.0.tar.gz",
            version="0.1.0",
            expected_checksum="abc123"
        )
        
        # Verify version directory was created
        version_dir = os.path.join(self.temp_dir, "0.1.0")
        self.assertTrue(os.path.exists(version_dir))
        self.assertTrue(os.path.isdir(version_dir))


class TestUpdaterServiceInitialization(unittest.TestCase):
    """Tests for updater service initialization"""
    
    def setUp(self):
        """Set up test environment"""
        # Save original environment variables
        self.original_env = {
            'ROBOT_NAME': os.environ.get('ROBOT_NAME'),
            'AUTO_UPDATE': os.environ.get('AUTO_UPDATE'),
            'AUTO_UPDATE_CHANNEL': os.environ.get('AUTO_UPDATE_CHANNEL'),
            'AUTO_UPDATE_SCHEDULE_UTC': os.environ.get('AUTO_UPDATE_SCHEDULE_UTC'),
            'DOWNLOAD_DIR': os.environ.get('DOWNLOAD_DIR')
        }
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def test_service_initialization(self):
        """Test that service initializes with correct configuration"""
        os.environ['ROBOT_NAME'] = 'TestBot'
        os.environ['AUTO_UPDATE'] = 'false'
        os.environ['AUTO_UPDATE_CHANNEL'] = 'stable'
        os.environ['AUTO_UPDATE_SCHEDULE_UTC'] = '04:30'
        os.environ['DOWNLOAD_DIR'] = '/tmp/test'
        
        service = UpdaterService()
        
        self.assertEqual(service.robot_name, 'TestBot')
        self.assertFalse(service.auto_update)
        self.assertEqual(service.auto_update_channel, 'stable')
        self.assertEqual(service.auto_update_schedule_utc, '04:30')
        self.assertEqual(service.download_dir, '/tmp/test')
        self.assertTrue(service.running)
    
    def test_service_default_values(self):
        """Test that service uses default values when env vars not set"""
        # Clear environment variables
        os.environ.pop('ROBOT_NAME', None)
        os.environ.pop('AUTO_UPDATE', None)
        os.environ.pop('AUTO_UPDATE_CHANNEL', None)
        os.environ.pop('AUTO_UPDATE_SCHEDULE_UTC', None)
        os.environ.pop('DOWNLOAD_DIR', None)
        
        service = UpdaterService()
        
        self.assertEqual(service.robot_name, 'TurboPi')
        self.assertFalse(service.auto_update)
        self.assertEqual(service.auto_update_channel, 'stable')
        self.assertEqual(service.auto_update_schedule_utc, '03:00')
        self.assertEqual(service.download_dir, '/opt/turbopi/downloads')

    def test_service_invalid_channel_and_schedule_fall_back(self):
        """Test invalid channel/schedule values safely fall back to stable defaults."""
        os.environ['AUTO_UPDATE_CHANNEL'] = 'beta'
        os.environ['AUTO_UPDATE_SCHEDULE_UTC'] = '99:99'

        service = UpdaterService()

        self.assertEqual(service.auto_update_channel, 'stable')
        self.assertEqual(service.auto_update_schedule_utc, '03:00')


if __name__ == '__main__':
    unittest.main()
