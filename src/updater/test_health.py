#!/usr/bin/env python3
"""
Unit tests for health check module.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
from health import (
    check_service_status,
    wait_for_service,
    check_all_services,
    verify_release_health,
    get_service_logs,
    HealthCheckError
)


class TestCheckServiceStatus(unittest.TestCase):
    """Tests for service status checking"""
    
    @patch('subprocess.run')
    def test_check_service_status_active(self, mock_run):
        """Test that active service returns True"""
        mock_run.return_value = MagicMock(
            stdout='active\n',
            returncode=0
        )
        
        result = check_service_status('turbopi-api.service')
        
        self.assertTrue(result)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args, ['systemctl', 'is-active', 'turbopi-api.service'])
    
    @patch('subprocess.run')
    def test_check_service_status_inactive(self, mock_run):
        """Test that inactive service returns False"""
        mock_run.return_value = MagicMock(
            stdout='inactive\n',
            returncode=3
        )
        
        result = check_service_status('turbopi-api.service')
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_check_service_status_timeout(self, mock_run):
        """Test that timeout returns False"""
        mock_run.side_effect = subprocess.TimeoutExpired('systemctl', 10)
        
        result = check_service_status('turbopi-api.service')
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_check_service_status_error(self, mock_run):
        """Test that errors return False"""
        mock_run.side_effect = Exception("Test error")
        
        result = check_service_status('turbopi-api.service')
        
        self.assertFalse(result)


class TestWaitForService(unittest.TestCase):
    """Tests for waiting for service to become active"""
    
    @patch('health.check_service_status')
    @patch('time.sleep')
    def test_wait_for_service_immediate_success(self, mock_sleep, mock_check):
        """Test service that is immediately active"""
        mock_check.return_value = True
        
        result = wait_for_service('turbopi-api.service', timeout=10, poll_interval=1)
        
        self.assertTrue(result)
        mock_check.assert_called_once_with('turbopi-api.service')
        mock_sleep.assert_not_called()  # No wait needed
    
    @patch('health.check_service_status')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_service_becomes_active(self, mock_time, mock_sleep, mock_check):
        """Test service that becomes active after waiting"""
        # Simulate time progression
        # More time values needed to account for all time.time() calls in the function
        mock_time.side_effect = [0, 2, 2, 4, 4, 6]  # Multiple calls per iteration
        mock_check.side_effect = [False, True]  # Inactive first, then active
        
        result = wait_for_service('turbopi-api.service', timeout=10, poll_interval=2)
        
        self.assertTrue(result)
        self.assertEqual(mock_check.call_count, 2)
    
    @patch('health.check_service_status')
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_service_timeout(self, mock_time, mock_sleep, mock_check):
        """Test service that never becomes active"""
        # Simulate time progression past timeout
        mock_time.side_effect = [0, 2, 4, 6, 8, 10, 12]
        mock_check.return_value = False  # Always inactive
        
        result = wait_for_service('turbopi-api.service', timeout=10, poll_interval=2)
        
        self.assertFalse(result)


class TestCheckAllServices(unittest.TestCase):
    """Tests for checking all services"""
    
    @patch('health.wait_for_service')
    def test_check_all_services_all_healthy(self, mock_wait):
        """Test when all services are healthy"""
        mock_wait.return_value = True
        
        results = check_all_services(timeout_per_service=10)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(results.values()))
        
        # Verify all three services were checked
        expected_services = ['turbopi-api.service', 'turbopi-ui.service', 'turbopi-updater.service']
        actual_services = [call[0][0] for call in mock_wait.call_args_list]
        self.assertEqual(set(actual_services), set(expected_services))
    
    @patch('health.wait_for_service')
    def test_check_all_services_one_unhealthy(self, mock_wait):
        """Test when one service is unhealthy"""
        # API and updater healthy, UI unhealthy
        mock_wait.side_effect = [True, False, True]
        
        results = check_all_services(timeout_per_service=10)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(results['turbopi-api.service'])
        self.assertFalse(results['turbopi-ui.service'])
        self.assertTrue(results['turbopi-updater.service'])


class TestVerifyReleaseHealth(unittest.TestCase):
    """Tests for complete release health verification"""
    
    @patch('health.check_all_services')
    @patch('time.sleep')
    def test_verify_release_health_success(self, mock_sleep, mock_check_all):
        """Test successful health check"""
        mock_check_all.return_value = {
            'turbopi-api.service': True,
            'turbopi-ui.service': True,
            'turbopi-updater.service': True
        }
        
        result = verify_release_health(timeout=60)
        
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(5)  # Initial wait
    
    @patch('health.check_all_services')
    @patch('time.sleep')
    def test_verify_release_health_failure(self, mock_sleep, mock_check_all):
        """Test failed health check"""
        mock_check_all.return_value = {
            'turbopi-api.service': True,
            'turbopi-ui.service': False,  # UI failed
            'turbopi-updater.service': True
        }
        
        result = verify_release_health(timeout=60)
        
        self.assertFalse(result)
    
    @patch('health.check_all_services')
    @patch('time.sleep')
    def test_verify_release_health_all_failed(self, mock_sleep, mock_check_all):
        """Test when all services fail"""
        mock_check_all.return_value = {
            'turbopi-api.service': False,
            'turbopi-ui.service': False,
            'turbopi-updater.service': False
        }
        
        result = verify_release_health(timeout=60)
        
        self.assertFalse(result)


class TestGetServiceLogs(unittest.TestCase):
    """Tests for getting service logs"""
    
    @patch('subprocess.run')
    def test_get_service_logs_success(self, mock_run):
        """Test successful log retrieval"""
        mock_run.return_value = MagicMock(
            stdout='Log line 1\nLog line 2\n',
            stderr='',
            returncode=0
        )
        
        logs = get_service_logs('turbopi-api.service', lines=50)
        
        self.assertIsNotNone(logs)
        self.assertIn('Log line 1', logs)
        self.assertIn('Log line 2', logs)
        
        # Verify correct command
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], 'journalctl')
        self.assertIn('-u', call_args)
        self.assertIn('turbopi-api.service', call_args)
        self.assertIn('-n', call_args)
        self.assertIn('50', call_args)
    
    @patch('subprocess.run')
    def test_get_service_logs_failure(self, mock_run):
        """Test log retrieval failure"""
        mock_run.return_value = MagicMock(
            stdout='',
            stderr='Error',
            returncode=1
        )
        
        logs = get_service_logs('turbopi-api.service', lines=50)
        
        self.assertIsNone(logs)
    
    @patch('subprocess.run')
    def test_get_service_logs_timeout(self, mock_run):
        """Test log retrieval timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired('journalctl', 10)
        
        logs = get_service_logs('turbopi-api.service', lines=50)
        
        self.assertIsNone(logs)


if __name__ == '__main__':
    unittest.main()
