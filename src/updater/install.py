#!/usr/bin/env python3
"""
Installation module for TurboPi updates.

This module handles:
- Extraction of update artifacts to versioned release directories
- Validation of extracted contents
- Creation of release metadata
- Atomic directory operations

Follows docs/updater/RELEASE_INSTALL_LAYOUT.md and docs/updater/PROTOCOL.md
"""

import os
import tarfile
import json
import logging
import shutil
from datetime import datetime, timezone
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class InstallError(Exception):
    """Exception raised when installation fails"""
    pass


def extract_tarball(tarball_path: str, dest_dir: str) -> None:
    """
    Extract a tarball to the destination directory.
    
    Args:
        tarball_path: Path to the .tar.gz file
        dest_dir: Directory to extract to (should be /opt/turbopi/releases/<version>)
        
    Raises:
        InstallError: If extraction fails
    """
    logger.info(f"Extracting {tarball_path} to {dest_dir}")
    
    # Validate tarball exists
    if not os.path.exists(tarball_path):
        raise InstallError(f"Tarball not found: {tarball_path}")
    
    # Create destination directory
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        raise InstallError(f"Failed to create destination directory {dest_dir}: {e}")
    
    # Extract tarball
    try:
        with tarfile.open(tarball_path, 'r:gz') as tar:
            # Security: Check for path traversal attacks
            for member in tar.getmembers():
                member_path = os.path.normpath(member.name)
                if member_path.startswith('..') or os.path.isabs(member_path):
                    raise InstallError(f"Unsafe path in tarball: {member.name}")
            
            # Extract all files
            tar.extractall(dest_dir)
            logger.info(f"Extracted {len(tar.getmembers())} files")
            
    except tarfile.TarError as e:
        raise InstallError(f"Failed to extract tarball: {e}")
    except Exception as e:
        raise InstallError(f"Unexpected error during extraction: {e}")
    
    logger.info(f"Extraction complete: {dest_dir}")


def validate_release_structure(release_dir: str) -> None:
    """
    Validate that the extracted release has the expected structure.
    
    Expected structure:
      releases/<version>/
        bin/           # Service launcher scripts
        src/           # Service implementations
          api/
          ui/
          updater/
    
    Args:
        release_dir: Path to the release directory to validate
        
    Raises:
        InstallError: If structure is invalid
    """
    logger.info(f"Validating release structure: {release_dir}")
    
    # Check required directories
    required_dirs = [
        'bin',
        'src',
        'src/api',
        'src/ui',
        'src/updater'
    ]
    
    for dir_path in required_dirs:
        full_path = os.path.join(release_dir, dir_path)
        if not os.path.isdir(full_path):
            raise InstallError(f"Missing required directory: {dir_path}")
    
    # Check required executables
    required_bins = ['api', 'ui', 'updater']
    
    for bin_name in required_bins:
        bin_path = os.path.join(release_dir, 'bin', bin_name)
        if not os.path.exists(bin_path):
            raise InstallError(f"Missing required binary: bin/{bin_name}")
        if not os.access(bin_path, os.X_OK):
            raise InstallError(f"Binary not executable: bin/{bin_name}")
    
    logger.info("Release structure validation PASSED")


def create_metadata(
    release_dir: str,
    version: str,
    source_url: str,
    checksum: str,
    requires_reboot: bool = False
) -> None:
    """
    Create metadata.json for the installed release.
    
    Args:
        release_dir: Path to the release directory
        version: Version string (e.g., "0.1.0")
        source_url: URL the release was downloaded from
        checksum: SHA256 checksum of the tarball
        requires_reboot: Whether this release requires a reboot
        
    Raises:
        InstallError: If metadata creation fails
    """
    logger.info(f"Creating metadata for release {version}")
    
    metadata = {
        "version": version,
        "install_date": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "checksum": checksum,
        "requires_reboot": requires_reboot,
        "health_check_passed": False  # Will be updated after health check
    }
    
    metadata_path = os.path.join(release_dir, 'metadata.json')
    
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Created metadata: {metadata_path}")
    except OSError as e:
        raise InstallError(f"Failed to create metadata file: {e}")


def update_metadata_health_status(release_dir: str, passed: bool) -> None:
    """
    Update the health_check_passed field in metadata.json.
    
    Args:
        release_dir: Path to the release directory
        passed: Whether the health check passed
        
    Raises:
        InstallError: If metadata update fails
    """
    metadata_path = os.path.join(release_dir, 'metadata.json')
    
    if not os.path.exists(metadata_path):
        raise InstallError(f"Metadata file not found: {metadata_path}")
    
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        metadata['health_check_passed'] = passed
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Updated health check status: {passed}")
    except (OSError, json.JSONDecodeError) as e:
        raise InstallError(f"Failed to update metadata: {e}")


def install_release(
    tarball_path: str,
    version: str,
    releases_base: str = '/opt/turbopi/releases',
    source_url: str = '',
    checksum: str = '',
    requires_reboot: bool = False
) -> str:
    """
    Install a release from a tarball.
    
    This performs the complete installation:
    1. Extract tarball to releases/<version>/
    2. Validate structure
    3. Create metadata
    
    Args:
        tarball_path: Path to the downloaded tarball
        version: Version string (e.g., "0.1.0")
        releases_base: Base directory for releases (default: /opt/turbopi/releases)
        source_url: URL the release was downloaded from
        checksum: SHA256 checksum of the tarball
        requires_reboot: Whether this release requires a reboot
        
    Returns:
        Path to the installed release directory
        
    Raises:
        InstallError: If installation fails
    """
    logger.info(f"Installing release {version}")
    
    release_dir = os.path.join(releases_base, version)
    
    # Check if release already exists
    if os.path.exists(release_dir):
        logger.warning(f"Release directory already exists: {release_dir}")
        # Clean up existing directory
        try:
            shutil.rmtree(release_dir)
            logger.info(f"Removed existing release directory")
        except OSError as e:
            raise InstallError(f"Failed to remove existing release directory: {e}")
    
    try:
        # Extract tarball
        extract_tarball(tarball_path, release_dir)
        
        # Validate structure
        validate_release_structure(release_dir)
        
        # Create metadata
        create_metadata(release_dir, version, source_url, checksum, requires_reboot)
        
        logger.info(f"Release {version} installed successfully to {release_dir}")
        return release_dir
        
    except InstallError:
        # Clean up on failure
        logger.error(f"Installation failed, cleaning up {release_dir}")
        if os.path.exists(release_dir):
            try:
                shutil.rmtree(release_dir)
                logger.info("Cleaned up failed installation")
            except OSError as e:
                logger.error(f"Failed to clean up: {e}")
        raise


def get_release_metadata(release_dir: str) -> Optional[Dict]:
    """
    Read metadata for a release.
    
    Args:
        release_dir: Path to the release directory
        
    Returns:
        Metadata dictionary, or None if not found
    """
    metadata_path = os.path.join(release_dir, 'metadata.json')
    
    if not os.path.exists(metadata_path):
        logger.warning(f"Metadata not found: {metadata_path}")
        return None
    
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read metadata: {e}")
        return None
