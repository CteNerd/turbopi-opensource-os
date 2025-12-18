#!/usr/bin/env python3
"""
Integration test for complete update application flow.

This demonstrates the end-to-end update process in a simulated environment.
"""

import os
import tempfile
import shutil
import tarfile
import unittest
from unittest.mock import patch
from apply import apply_update
from install import create_metadata


class TestApplyUpdateIntegration(unittest.TestCase):
    """Integration test for complete update flow"""
    
    def setUp(self):
        """Set up test environment with simulated TurboPi structure"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create directory structure
        self.download_dir = os.path.join(self.temp_dir, 'downloads')
        self.releases_base = os.path.join(self.temp_dir, 'releases')
        self.turbopi_root = self.temp_dir
        
        os.makedirs(self.download_dir)
        os.makedirs(self.releases_base)
        
        # Create "old" release (0.0.9)
        self.create_release('0.0.9')
        
        # Create current and previous symlinks pointing to old release
        old_release_path = os.path.join(self.releases_base, '0.0.9')
        current_link = os.path.join(self.turbopi_root, 'current')
        previous_link = os.path.join(self.turbopi_root, 'previous')
        
        os.symlink(old_release_path, current_link)
        os.symlink(old_release_path, previous_link)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_release(self, version):
        """Helper to create a valid release directory"""
        release_dir = os.path.join(self.releases_base, version)
        
        # Create structure
        os.makedirs(os.path.join(release_dir, 'bin'))
        os.makedirs(os.path.join(release_dir, 'src', 'api'))
        os.makedirs(os.path.join(release_dir, 'src', 'ui'))
        os.makedirs(os.path.join(release_dir, 'src', 'updater'))
        
        # Create executable binaries
        for bin_name in ['api', 'ui', 'updater']:
            bin_path = os.path.join(release_dir, 'bin', bin_name)
            with open(bin_path, 'w') as f:
                f.write('#!/bin/bash\necho "Version ' + version + '"')
            os.chmod(bin_path, 0o755)
        
        # Create service files
        for service in ['api', 'ui', 'updater']:
            service_file = os.path.join(release_dir, 'src', service, 'main.py')
            with open(service_file, 'w') as f:
                f.write(f'# Version {version}\nprint("Running {service}")')
        
        # Create metadata
        create_metadata(
            release_dir,
            version=version,
            source_url=f'http://example.com/turbopi-{version}.tar.gz',
            checksum='test123'
        )
        
        return release_dir
    
    def create_test_tarball(self, version):
        """Helper to create a tarball for a version"""
        # Create release structure in temp build dir
        build_dir = os.path.join(self.temp_dir, 'build', version)
        os.makedirs(os.path.join(build_dir, 'bin'))
        os.makedirs(os.path.join(build_dir, 'src', 'api'))
        os.makedirs(os.path.join(build_dir, 'src', 'ui'))
        os.makedirs(os.path.join(build_dir, 'src', 'updater'))
        
        # Create executable binaries
        for bin_name in ['api', 'ui', 'updater']:
            bin_path = os.path.join(build_dir, 'bin', bin_name)
            with open(bin_path, 'w') as f:
                f.write('#!/bin/bash\necho "Version ' + version + '"')
            os.chmod(bin_path, 0o755)
        
        # Create service files
        for service in ['api', 'ui', 'updater']:
            service_file = os.path.join(build_dir, 'src', service, 'main.py')
            with open(service_file, 'w') as f:
                f.write(f'# Version {version}\nprint("Running {service}")')
        
        # Create tarball
        version_download_dir = os.path.join(self.download_dir, version)
        os.makedirs(version_download_dir, exist_ok=True)
        tarball_path = os.path.join(version_download_dir, f'turbopi-{version}.tar.gz')
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            for item in os.listdir(build_dir):
                tar.add(
                    os.path.join(build_dir, item),
                    arcname=item
                )
        
        return tarball_path
    
    @patch('apply.download_and_verify')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    def test_successful_update_flow(
        self,
        mock_health,
        mock_restart,
        mock_download
    ):
        """Test complete successful update from 0.0.9 to 0.1.0"""
        new_version = '0.1.0'
        
        # Create tarball for new version
        self.create_test_tarball(new_version)
        
        # Mock successful operations
        mock_download.return_value = None
        mock_restart.return_value = True
        mock_health.return_value = True
        
        # Execute update
        result = apply_update(
            version=new_version,
            download_url=f'http://example.com/turbopi-{new_version}.tar.gz',
            checksum='abc123',
            download_dir=self.download_dir,
            releases_base=self.releases_base,
            turbopi_root=self.turbopi_root,
            skip_download=True  # Use pre-created tarball
        )
        
        # Verify success
        self.assertTrue(result)
        
        # Verify new release was created
        new_release_dir = os.path.join(self.releases_base, new_version)
        self.assertTrue(os.path.exists(new_release_dir))
        
        # Verify symlinks were updated
        current_link = os.path.join(self.turbopi_root, 'current')
        previous_link = os.path.join(self.turbopi_root, 'previous')
        
        self.assertTrue(os.path.islink(current_link))
        self.assertTrue(os.path.islink(previous_link))
        
        # Verify current points to new release
        current_target = os.readlink(current_link)
        self.assertIn(new_version, current_target)
        
        # Verify previous points to old release
        previous_target = os.readlink(previous_link)
        self.assertIn('0.0.9', previous_target)
        
        # Verify metadata was created
        metadata_path = os.path.join(new_release_dir, 'metadata.json')
        self.assertTrue(os.path.exists(metadata_path))
    
    @patch('apply.download_and_verify')
    @patch('apply.restart_services')
    @patch('apply.verify_release_health')
    def test_failed_update_with_rollback(
        self,
        mock_health,
        mock_restart,
        mock_download
    ):
        """Test update failure with successful rollback to 0.0.9"""
        new_version = '0.1.0'
        
        # Create tarball for new version
        self.create_test_tarball(new_version)
        
        # Mock operations: health check fails on new version, succeeds on rollback
        mock_download.return_value = None
        mock_restart.return_value = True
        mock_health.side_effect = [False, True]  # Fail new, succeed rollback
        
        # Execute update
        result = apply_update(
            version=new_version,
            download_url=f'http://example.com/turbopi-{new_version}.tar.gz',
            checksum='abc123',
            download_dir=self.download_dir,
            releases_base=self.releases_base,
            turbopi_root=self.turbopi_root,
            skip_download=True
        )
        
        # Verify update failed
        self.assertFalse(result)
        
        # Verify we rolled back - current should still point to 0.0.9
        current_link = os.path.join(self.turbopi_root, 'current')
        current_target = os.readlink(current_link)
        self.assertIn('0.0.9', current_target)
        
        # Verify health check was called twice (for update and rollback)
        self.assertEqual(mock_health.call_count, 2)
        
        # Verify services were restarted twice (for update and rollback)
        self.assertEqual(mock_restart.call_count, 2)
    
    @patch('apply.download_and_verify')
    def test_multiple_sequential_updates(
        self,
        mock_download
    ):
        """Test applying multiple updates sequentially: 0.0.9 → 0.1.0 → 0.1.1"""
        
        # Mock operations
        mock_download.return_value = None
        
        with patch('apply.restart_services', return_value=True):
            with patch('apply.verify_release_health', return_value=True):
                # First update: 0.0.9 → 0.1.0
                self.create_test_tarball('0.1.0')
                result_1 = apply_update(
                    version='0.1.0',
                    download_url='http://example.com/turbopi-0.1.0.tar.gz',
                    checksum='abc123',
                    download_dir=self.download_dir,
                    releases_base=self.releases_base,
                    turbopi_root=self.turbopi_root,
                    skip_download=True
                )
                self.assertTrue(result_1)
                
                # Verify state after first update
                current_link = os.path.join(self.turbopi_root, 'current')
                current_target = os.readlink(current_link)
                self.assertIn('0.1.0', current_target)
                
                # Second update: 0.1.0 → 0.1.1
                self.create_test_tarball('0.1.1')
                result_2 = apply_update(
                    version='0.1.1',
                    download_url='http://example.com/turbopi-0.1.1.tar.gz',
                    checksum='def456',
                    download_dir=self.download_dir,
                    releases_base=self.releases_base,
                    turbopi_root=self.turbopi_root,
                    skip_download=True
                )
                self.assertTrue(result_2)
                
                # Verify final state
                current_target = os.readlink(current_link)
                self.assertIn('0.1.1', current_target)
                
                previous_link = os.path.join(self.turbopi_root, 'previous')
                previous_target = os.readlink(previous_link)
                self.assertIn('0.1.0', previous_target)
                
                # Verify all three releases exist
                self.assertTrue(os.path.exists(os.path.join(self.releases_base, '0.0.9')))
                self.assertTrue(os.path.exists(os.path.join(self.releases_base, '0.1.0')))
                self.assertTrue(os.path.exists(os.path.join(self.releases_base, '0.1.1')))


if __name__ == '__main__':
    unittest.main()
