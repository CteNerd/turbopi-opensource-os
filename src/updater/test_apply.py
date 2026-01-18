#!/usr/bin/env python3
"""
Unit tests for update application orchestrator.
"""

import os
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
from apply import (
    get_symlink_target,
    atomic_symlink_update,
    restart_services,
    switch_to_release,
    rollback_to_previous,
    apply_update,
    UpdateError,
    RollbackError
)
from download import DownloadError, ChecksumError
from install import InstallError


class TestGetSymlinkTarget(unittest.TestCase):
    """Tests for getting symlink target"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_symlink_target_success(self):
        """Test reading valid symlink"""
        target = os.path.join(self.temp_dir, 'target')
        link = os.path.join(self.temp_dir, 'link')
        
        os.makedirs(target)
        os.symlink(target, link)
        
        result = get_symlink_target(link)
        self.assertEqual(result, target)
    
    def test_get_symlink_target_not_symlink(self):
        """Test returns None for non-symlink"""
        regular_file = os.path.join(self.temp_dir, 'file')
        with open(regular_file, 'w') as f:
            f.write('test')
        
        result = get_symlink_target(regular_file)
        self.assertIsNone(result)
    
    def test_get_symlink_target_not_exists(self):
        """Test returns None for non-existent path"""
        result = get_symlink_target('/nonexistent/path')
        self.assertIsNone(result)


class TestAtomicSymlinkUpdate(unittest.TestCase):
    """Tests for atomic symlink updates"""
    
    @patch('subprocess.run')
    def test_atomic_symlink_update_success(self, mock_run):
        """Test successful symlink update"""
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        
        atomic_symlink_update('/opt/turbopi/current', '/opt/turbopi/releases/0.1.0')
        
        # Verify ln -sfn was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], 'ln')
        self.assertIn('-sfn', call_args)
        self.assertIn('/opt/turbopi/releases/0.1.0', call_args)
        self.assertIn('/opt/turbopi/current', call_args)
    
    @patch('subprocess.run')
    def test_atomic_symlink_update_failure(self, mock_run):
        """Test symlink update failure"""
        mock_run.return_value = MagicMock(returncode=1, stderr='Error')
        
        with self.assertRaises(UpdateError):
            atomic_symlink_update('/opt/turbopi/current', '/opt/turbopi/releases/0.1.0')
    
    @patch('subprocess.run')
    def test_atomic_symlink_update_timeout(self, mock_run):
        """Test symlink update timeout"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('ln', 10)
        
        with self.assertRaises(UpdateError):
            atomic_symlink_update('/opt/turbopi/current', '/opt/turbopi/releases/0.1.0')


class TestRestartServices(unittest.TestCase):
    """Tests for service restart"""
    
    @patch('subprocess.run')
    def test_restart_services_success(self, mock_run):
        """Test successful restart of all services"""
        mock_run.return_value = MagicMock(returncode=0, stderr='')
        
        result = restart_services()
        
        self.assertTrue(result)
        
        # Verify all three services were restarted in order
        self.assertEqual(mock_run.call_count, 3)
        calls = mock_run.call_args_list
        
        self.assertIn('turbopi-api.service', calls[0][0][0])
        self.assertIn('turbopi-ui.service', calls[1][0][0])
        self.assertIn('turbopi-updater.service', calls[2][0][0])
    
    @patch('subprocess.run')
    def test_restart_services_first_fails(self, mock_run):
        """Test failure when first service restart fails"""
        mock_run.return_value = MagicMock(returncode=1, stderr='Error')
        
        result = restart_services()
        
        self.assertFalse(result)
        # Should stop after first failure
        self.assertEqual(mock_run.call_count, 1)
    
    @patch('subprocess.run')
    def test_restart_services_timeout(self, mock_run):
        """Test timeout during service restart"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('systemctl', 30)
        
        result = restart_services()
        
        self.assertFalse(result)


class TestSwitchToRelease(unittest.TestCase):
    """Tests for release switching"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.turbopi_root = self.temp_dir
        
        # Create release directories
        self.old_release = os.path.join(self.temp_dir, 'releases', '0.1.0')
        self.new_release = os.path.join(self.temp_dir, 'releases', '0.1.1')
        os.makedirs(self.old_release)
        os.makedirs(self.new_release)
        
        # Create current symlink pointing to old release
        current_link = os.path.join(self.temp_dir, 'current')
        os.symlink(self.old_release, current_link)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('apply.atomic_symlink_update')
    def test_switch_to_release_success(self, mock_update):
        """Test successful release switch"""
        old_current, old_previous = switch_to_release(
            self.new_release,
            self.turbopi_root
        )
        
        # Verify old_current captured correctly
        self.assertEqual(old_current, self.old_release)
        
        # Verify symlinks were updated in correct order
        self.assertEqual(mock_update.call_count, 2)
        calls = mock_update.call_args_list
        
        # First call: update previous to old current
        prev_link = os.path.join(self.turbopi_root, 'previous')
        self.assertEqual(calls[0][0], (prev_link, self.old_release))
        
        # Second call: update current to new release
        curr_link = os.path.join(self.turbopi_root, 'current')
        self.assertEqual(calls[1][0], (curr_link, self.new_release))
    
    @patch('apply.atomic_symlink_update')
    def test_switch_to_release_new_not_exists(self, mock_update):
        """Test error when new release doesn't exist"""
        nonexistent = os.path.join(self.temp_dir, 'releases', '0.9.9')
        
        with self.assertRaises(UpdateError) as cm:
            switch_to_release(nonexistent, self.turbopi_root)
        
        self.assertIn('does not exist', str(cm.exception))
        mock_update.assert_not_called()


class TestRollbackToPrevious(unittest.TestCase):
    """Tests for rollback functionality"""
    
    @patch('apply.atomic_symlink_update')
    def test_rollback_to_previous_success(self, mock_update):
        """Test successful rollback"""
        turbopi_root = '/opt/turbopi'
        old_current = '/opt/turbopi/releases/0.1.0'
        old_previous = '/opt/turbopi/releases/0.0.9'
        
        rollback_to_previous(old_current, old_previous, turbopi_root)
        
        # Verify symlinks were restored
        self.assertEqual(mock_update.call_count, 2)
        calls = mock_update.call_args_list
        
        # First: restore current
        curr_link = os.path.join(turbopi_root, 'current')
        self.assertEqual(calls[0][0], (curr_link, old_current))
        
        # Second: restore previous
        prev_link = os.path.join(turbopi_root, 'previous')
        self.assertEqual(calls[1][0], (prev_link, old_previous))
    
    def test_rollback_to_previous_no_previous(self):
        """Test error when no previous release available"""
        with self.assertRaises(RollbackError) as cm:
            rollback_to_previous(None, None, '/opt/turbopi')
        
        self.assertIn('no previous release', str(cm.exception))
    
    @patch('apply.atomic_symlink_update')
    def test_rollback_to_previous_symlink_fails(self, mock_update):
        """Test rollback failure"""
        mock_update.side_effect = UpdateError("Symlink failed")
        
        with self.assertRaises(RollbackError):
            rollback_to_previous(
                '/opt/turbopi/releases/0.1.0',
                '/opt/turbopi/releases/0.0.9',
                '/opt/turbopi'
            )


class TestApplyUpdate(unittest.TestCase):
    """Integration tests for complete update application"""
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_success(
        self,
        mock_update_meta,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test successful complete update flow"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        mock_health.return_value = True
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Verify success
        self.assertTrue(result)
        
        # Verify all steps were called
        mock_download.assert_called_once()
        mock_install.assert_called_once()
        mock_switch.assert_called_once()
        mock_restart.assert_called_once()
        mock_health.assert_called_once()
        mock_update_meta.assert_called_once_with('/opt/turbopi/releases/0.1.0', passed=True)
    
    @patch('apply.download_and_verify')
    def test_apply_update_download_failure(self, mock_download):
        """Test update aborts on download failure"""
        mock_download.side_effect = DownloadError("Network error")
        
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False without attempting other steps
        self.assertFalse(result)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    def test_apply_update_install_failure(self, mock_install, mock_download):
        """Test update aborts on install failure"""
        mock_install.side_effect = InstallError("Extract failed")
        
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False
        self.assertFalse(result)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_health_failure_rollback_success(
        self,
        mock_update_meta,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test rollback on health check failure"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        
        # First health check (new version) fails, second (after rollback) succeeds
        mock_health.side_effect = [False, True]
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False (update failed)
        self.assertFalse(result)
        
        # Verify rollback was attempted
        mock_rollback.assert_called_once()
        
        # Verify services were restarted twice (for update and rollback)
        self.assertEqual(mock_restart.call_count, 2)
        
        # Verify health check was called twice
        self.assertEqual(mock_health.call_count, 2)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    def test_apply_update_rollback_failure(
        self,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test critical error when rollback fails"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        mock_health.return_value = False  # Health check fails
        mock_rollback.side_effect = RollbackError("Rollback failed")
        
        # Execute update - should raise UpdateError
        with self.assertRaises(UpdateError) as cm:
            apply_update(
                version='0.1.0',
                download_url='http://example.com/release.tar.gz',
                checksum='abc123'
            )
        
        self.assertIn('rollback failed', str(cm.exception).lower())
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_skip_download(
        self,
        mock_update_meta,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test update with skip_download when tarball exists"""
        # Create temporary tarball
        temp_dir = tempfile.mkdtemp()
        try:
            tarball_path = os.path.join(temp_dir, '0.1.0', 'turbopi-0.1.0.tar.gz')
            os.makedirs(os.path.dirname(tarball_path))
            with open(tarball_path, 'w') as f:
                f.write('fake tarball')
            
            # Setup mocks
            mock_install.return_value = '/opt/turbopi/releases/0.1.0'
            mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
            mock_restart.return_value = True
            mock_health.return_value = True
            
            # Execute update with skip_download
            result = apply_update(
                version='0.1.0',
                download_url='http://example.com/release.tar.gz',
                checksum='abc123',
                download_dir=temp_dir,
                skip_download=True
            )
            
            # Verify success
            self.assertTrue(result)
            
            # Verify download was NOT called
            mock_download.assert_not_called()
            
            # Verify other steps were called
            mock_install.assert_called_once()
            mock_switch.assert_called_once()
            mock_restart.assert_called_once()
            mock_health.assert_called_once()
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_requires_reboot(
        self,
        mock_update_meta,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test update with requires_reboot flag"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        mock_health.return_value = True
        
        # Execute update with requires_reboot
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123',
            requires_reboot=True
        )
        
        # Verify success
        self.assertTrue(result)
        
        # Verify install was called with requires_reboot=True
        install_call_kwargs = mock_install.call_args[1]
        self.assertTrue(install_call_kwargs.get('requires_reboot'))
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_restart_failure_rollback(
        self,
        mock_update_meta,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test rollback when service restart fails after switch"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        
        # First restart (after switch) fails, second (after rollback) succeeds
        mock_restart.side_effect = [False, True]
        
        # Health check after rollback succeeds
        mock_health.return_value = True
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False (update failed)
        self.assertFalse(result)
        
        # Verify rollback was attempted
        mock_rollback.assert_called_once_with(
            '/opt/turbopi/releases/0.0.9',
            None,
            '/opt/turbopi'
        )
        
        # Verify restart was called twice
        self.assertEqual(mock_restart.call_count, 2)
        
        # Verify health check was called after rollback
        self.assertEqual(mock_health.call_count, 1)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    def test_apply_update_rollback_restart_failure(
        self,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test critical error when rollback restart fails"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        
        # First restart succeeds, health check fails
        mock_restart.side_effect = [True, False]  # Second restart (after rollback) fails
        mock_health.return_value = False
        
        # Execute update - should raise UpdateError
        with self.assertRaises(UpdateError) as cm:
            apply_update(
                version='0.1.0',
                download_url='http://example.com/release.tar.gz',
                checksum='abc123'
            )
        
        self.assertIn('rollback', str(cm.exception).lower())
        
        # Verify rollback was attempted
        mock_rollback.assert_called_once()
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    def test_apply_update_rollback_health_failure(
        self,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test critical error when rollback health check fails"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        
        # Both health checks fail
        mock_health.return_value = False
        
        # Execute update - should raise UpdateError
        with self.assertRaises(UpdateError) as cm:
            apply_update(
                version='0.1.0',
                download_url='http://example.com/release.tar.gz',
                checksum='abc123'
            )
        
        self.assertIn('rollback', str(cm.exception).lower())
        
        # Verify rollback was attempted
        mock_rollback.assert_called_once()
        
        # Verify health check was called twice
        self.assertEqual(mock_health.call_count, 2)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_rollback_metadata_failure_non_critical(
        self,
        mock_update_meta,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test rollback succeeds even if metadata update fails"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        
        # First health check fails, second succeeds
        mock_health.side_effect = [False, True]
        
        # Metadata update fails (should not prevent rollback success)
        mock_update_meta.side_effect = InstallError("Metadata write failed")
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False (update failed, but rollback succeeded)
        self.assertFalse(result)
        
        # Verify rollback completed successfully despite metadata failure
        mock_rollback.assert_called_once()
        mock_update_meta.assert_called_once()
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    @patch('apply.update_metadata_health_status')
    def test_apply_update_rollback_metadata_oserror_non_critical(
        self,
        mock_update_meta,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test rollback succeeds even if metadata update raises OSError"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.return_value = ('/opt/turbopi/releases/0.0.9', None)
        mock_restart.return_value = True
        
        # First health check fails, second succeeds
        mock_health.side_effect = [False, True]
        
        # Metadata update raises OSError (should not prevent rollback success)
        mock_update_meta.side_effect = OSError("Permission denied")
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False (update failed, but rollback succeeded)
        self.assertFalse(result)
        
        # Verify rollback completed successfully despite metadata failure
        mock_rollback.assert_called_once()
        mock_update_meta.assert_called_once()
    
    @patch('apply.download_and_verify')
    def test_apply_update_checksum_failure(self, mock_download):
        """Test update aborts on checksum verification failure"""
        mock_download.side_effect = ChecksumError("Checksum mismatch")
        
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False without attempting rollback
        self.assertFalse(result)
    
    @patch('apply.download_and_verify')
    @patch('apply.install_release')
    @patch('apply.switch_to_release')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    @patch('apply.rollback_to_previous')
    def test_apply_update_switch_failure_no_rollback(
        self,
        mock_rollback,
        mock_health,
        mock_restart,
        mock_switch,
        mock_install,
        mock_download
    ):
        """Test no rollback when symlink switch fails (old_current is None)"""
        # Setup mocks
        mock_install.return_value = '/opt/turbopi/releases/0.1.0'
        mock_switch.side_effect = UpdateError("Symlink switch failed")
        
        # Execute update
        result = apply_update(
            version='0.1.0',
            download_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Should return False
        self.assertFalse(result)
        
        # Verify rollback was NOT attempted (switch failed, so old_current is None)
        mock_rollback.assert_not_called()
        
        # Verify restart was NOT called
        mock_restart.assert_not_called()


class TestSwitchToReleaseEdgeCases(unittest.TestCase):
    """Tests for edge cases in release switching"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.turbopi_root = self.temp_dir
        
        # Create new release directory
        self.new_release = os.path.join(self.temp_dir, 'releases', '0.1.1')
        os.makedirs(self.new_release)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('apply.atomic_symlink_update')
    def test_switch_to_release_no_previous_symlink(self, mock_update):
        """Test release switch when no previous symlink exists"""
        # No current symlink exists (fresh install scenario)
        old_current, old_previous = switch_to_release(
            self.new_release,
            self.turbopi_root
        )
        
        # Verify old_current is None
        self.assertIsNone(old_current)
        self.assertIsNone(old_previous)
        
        # Verify only current symlink was created (no previous update)
        self.assertEqual(mock_update.call_count, 1)
        
        # Verify current was set to new release
        curr_link = os.path.join(self.turbopi_root, 'current')
        self.assertEqual(mock_update.call_args[0], (curr_link, self.new_release))


class TestRollbackToPreviousEdgeCases(unittest.TestCase):
    """Tests for edge cases in rollback functionality"""
    
    @patch('apply.atomic_symlink_update')
    def test_rollback_no_old_previous(self, mock_update):
        """Test rollback with no old_previous (maintains chain)"""
        turbopi_root = '/opt/turbopi'
        old_current = '/opt/turbopi/releases/0.1.0'
        old_previous = None  # No previous-previous release
        
        rollback_to_previous(old_current, old_previous, turbopi_root)
        
        # Verify only current was restored (no previous update since old_previous is None)
        self.assertEqual(mock_update.call_count, 1)
        
        # Verify current was restored
        curr_link = os.path.join(turbopi_root, 'current')
        self.assertEqual(mock_update.call_args[0], (curr_link, old_current))


if __name__ == '__main__':
    unittest.main()
