#!/usr/bin/env python3
"""
Unit tests for install module.
"""

import os
import json
import tempfile
import tarfile
import shutil
import unittest
from install import (
    extract_tarball,
    validate_release_structure,
    create_metadata,
    update_metadata_health_status,
    install_release,
    get_release_metadata,
    InstallError
)


class TestExtractTarball(unittest.TestCase):
    """Tests for tarball extraction"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_tarball_success(self):
        """Test successful tarball extraction"""
        # Create a test tarball
        tarball_path = os.path.join(self.temp_dir, 'test.tar.gz')
        dest_dir = os.path.join(self.temp_dir, 'extracted')
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Create a test file
            test_file = os.path.join(self.temp_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test content')
            tar.add(test_file, arcname='test.txt')
        
        # Extract
        extract_tarball(tarball_path, dest_dir)
        
        # Verify extraction
        self.assertTrue(os.path.exists(os.path.join(dest_dir, 'test.txt')))
        with open(os.path.join(dest_dir, 'test.txt'), 'r') as f:
            self.assertEqual(f.read(), 'test content')
    
    def test_extract_tarball_missing_file(self):
        """Test error when tarball doesn't exist"""
        dest_dir = os.path.join(self.temp_dir, 'extracted')
        
        with self.assertRaises(InstallError):
            extract_tarball('/nonexistent/file.tar.gz', dest_dir)
    
    def test_extract_tarball_path_traversal(self):
        """Test that path traversal attacks are blocked"""
        tarball_path = os.path.join(self.temp_dir, 'malicious.tar.gz')
        dest_dir = os.path.join(self.temp_dir, 'extracted')
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            # Try to create a file with path traversal
            test_file = os.path.join(self.temp_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('malicious')
            
            # Add with dangerous name
            tar.add(test_file, arcname='../../../etc/passwd')
        
        # Should raise error
        with self.assertRaises(InstallError) as cm:
            extract_tarball(tarball_path, dest_dir)
        
        self.assertIn('Unsafe path', str(cm.exception))


class TestValidateReleaseStructure(unittest.TestCase):
    """Tests for release structure validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_valid_structure(self, base_dir):
        """Helper to create a valid release structure"""
        os.makedirs(os.path.join(base_dir, 'bin'))
        os.makedirs(os.path.join(base_dir, 'src', 'api'))
        os.makedirs(os.path.join(base_dir, 'src', 'ui'))
        os.makedirs(os.path.join(base_dir, 'src', 'updater'))
        
        # Create executable binaries
        for bin_name in ['api', 'ui', 'updater']:
            bin_path = os.path.join(base_dir, 'bin', bin_name)
            with open(bin_path, 'w') as f:
                f.write('#!/bin/bash\necho test')
            os.chmod(bin_path, 0o755)
    
    def test_validate_release_structure_valid(self):
        """Test validation passes for valid structure"""
        release_dir = os.path.join(self.temp_dir, 'release')
        self.create_valid_structure(release_dir)
        
        # Should not raise
        validate_release_structure(release_dir)
    
    def test_validate_release_structure_missing_bin(self):
        """Test validation fails if bin directory missing"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(os.path.join(release_dir, 'src', 'api'))
        os.makedirs(os.path.join(release_dir, 'src', 'ui'))
        os.makedirs(os.path.join(release_dir, 'src', 'updater'))
        
        with self.assertRaises(InstallError) as cm:
            validate_release_structure(release_dir)
        
        self.assertIn('bin', str(cm.exception))
    
    def test_validate_release_structure_missing_service_dir(self):
        """Test validation fails if service directory missing"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(os.path.join(release_dir, 'bin'))
        os.makedirs(os.path.join(release_dir, 'src', 'api'))
        os.makedirs(os.path.join(release_dir, 'src', 'ui'))
        # Missing src/updater
        
        with self.assertRaises(InstallError) as cm:
            validate_release_structure(release_dir)
        
        self.assertIn('updater', str(cm.exception))
    
    def test_validate_release_structure_missing_binary(self):
        """Test validation fails if binary missing"""
        release_dir = os.path.join(self.temp_dir, 'release')
        self.create_valid_structure(release_dir)
        
        # Remove one binary
        os.remove(os.path.join(release_dir, 'bin', 'api'))
        
        with self.assertRaises(InstallError) as cm:
            validate_release_structure(release_dir)
        
        self.assertIn('api', str(cm.exception))
    
    def test_validate_release_structure_not_executable(self):
        """Test validation fails if binary not executable"""
        release_dir = os.path.join(self.temp_dir, 'release')
        self.create_valid_structure(release_dir)
        
        # Make binary non-executable
        bin_path = os.path.join(release_dir, 'bin', 'api')
        os.chmod(bin_path, 0o644)
        
        with self.assertRaises(InstallError) as cm:
            validate_release_structure(release_dir)
        
        self.assertIn('executable', str(cm.exception).lower())


class TestCreateMetadata(unittest.TestCase):
    """Tests for metadata creation"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_metadata_success(self):
        """Test successful metadata creation"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        create_metadata(
            release_dir,
            version='0.1.0',
            source_url='http://example.com/release.tar.gz',
            checksum='abc123',
            requires_reboot=False
        )
        
        # Verify metadata file exists
        metadata_path = os.path.join(release_dir, 'metadata.json')
        self.assertTrue(os.path.exists(metadata_path))
        
        # Verify content
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['version'], '0.1.0')
        self.assertEqual(metadata['source_url'], 'http://example.com/release.tar.gz')
        self.assertEqual(metadata['checksum'], 'abc123')
        self.assertEqual(metadata['requires_reboot'], False)
        self.assertEqual(metadata['health_check_passed'], False)
        self.assertIn('install_date', metadata)
    
    def test_create_metadata_with_reboot(self):
        """Test metadata creation with reboot flag"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        create_metadata(
            release_dir,
            version='0.2.0',
            source_url='http://example.com/release.tar.gz',
            checksum='def456',
            requires_reboot=True
        )
        
        metadata_path = os.path.join(release_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['requires_reboot'], True)


class TestUpdateMetadataHealthStatus(unittest.TestCase):
    """Tests for metadata health status updates"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_update_metadata_health_status_success(self):
        """Test successful health status update"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        # Create initial metadata
        create_metadata(
            release_dir,
            version='0.1.0',
            source_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Update health status
        update_metadata_health_status(release_dir, passed=True)
        
        # Verify update
        metadata_path = os.path.join(release_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata['health_check_passed'], True)
    
    def test_update_metadata_health_status_missing_file(self):
        """Test error when metadata file doesn't exist"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        with self.assertRaises(InstallError):
            update_metadata_health_status(release_dir, passed=True)


class TestGetReleaseMetadata(unittest.TestCase):
    """Tests for reading release metadata"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_release_metadata_success(self):
        """Test successful metadata reading"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        # Create metadata
        create_metadata(
            release_dir,
            version='0.1.0',
            source_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Read metadata
        metadata = get_release_metadata(release_dir)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['version'], '0.1.0')
    
    def test_get_release_metadata_missing_file(self):
        """Test None returned when metadata doesn't exist"""
        release_dir = os.path.join(self.temp_dir, 'release')
        os.makedirs(release_dir)
        
        metadata = get_release_metadata(release_dir)
        
        self.assertIsNone(metadata)


class TestInstallRelease(unittest.TestCase):
    """Integration tests for complete release installation"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.releases_base = os.path.join(self.temp_dir, 'releases')
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_tarball(self, version='0.1.0'):
        """Helper to create a valid test tarball"""
        # Create release structure
        build_dir = os.path.join(self.temp_dir, 'build')
        os.makedirs(os.path.join(build_dir, 'bin'))
        os.makedirs(os.path.join(build_dir, 'src', 'api'))
        os.makedirs(os.path.join(build_dir, 'src', 'ui'))
        os.makedirs(os.path.join(build_dir, 'src', 'updater'))
        
        # Create executable binaries
        for bin_name in ['api', 'ui', 'updater']:
            bin_path = os.path.join(build_dir, 'bin', bin_name)
            with open(bin_path, 'w') as f:
                f.write('#!/bin/bash\necho test')
            os.chmod(bin_path, 0o755)
        
        # Create service files
        for service in ['api', 'ui', 'updater']:
            service_file = os.path.join(build_dir, 'src', service, 'main.py')
            with open(service_file, 'w') as f:
                f.write('print("test")')
        
        # Create tarball
        tarball_path = os.path.join(self.temp_dir, f'turbopi-{version}.tar.gz')
        with tarfile.open(tarball_path, 'w:gz') as tar:
            for item in os.listdir(build_dir):
                tar.add(
                    os.path.join(build_dir, item),
                    arcname=item
                )
        
        return tarball_path
    
    def test_install_release_success(self):
        """Test successful complete installation"""
        version = '0.1.0'
        tarball_path = self.create_test_tarball(version)
        
        release_dir = install_release(
            tarball_path,
            version,
            self.releases_base,
            source_url='http://example.com/release.tar.gz',
            checksum='abc123'
        )
        
        # Verify installation
        expected_dir = os.path.join(self.releases_base, version)
        self.assertEqual(release_dir, expected_dir)
        self.assertTrue(os.path.exists(expected_dir))
        
        # Verify structure
        self.assertTrue(os.path.exists(os.path.join(expected_dir, 'bin', 'api')))
        self.assertTrue(os.path.exists(os.path.join(expected_dir, 'src', 'api', 'main.py')))
        
        # Verify metadata
        metadata = get_release_metadata(expected_dir)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['version'], version)
        self.assertEqual(metadata['checksum'], 'abc123')
    
    def test_install_release_overwrites_existing(self):
        """Test that existing release is replaced"""
        version = '0.1.0'
        tarball_path = self.create_test_tarball(version)
        
        # Install first time
        release_dir = install_release(
            tarball_path,
            version,
            self.releases_base,
            source_url='http://example.com/v1.tar.gz',
            checksum='abc123'
        )
        
        # Create a marker file
        marker_path = os.path.join(release_dir, 'marker.txt')
        with open(marker_path, 'w') as f:
            f.write('old')
        
        # Install again
        release_dir = install_release(
            tarball_path,
            version,
            self.releases_base,
            source_url='http://example.com/v2.tar.gz',
            checksum='def456'
        )
        
        # Marker should be gone
        self.assertFalse(os.path.exists(marker_path))
        
        # Metadata should be updated
        metadata = get_release_metadata(release_dir)
        self.assertEqual(metadata['source_url'], 'http://example.com/v2.tar.gz')
        self.assertEqual(metadata['checksum'], 'def456')


if __name__ == '__main__':
    unittest.main()
