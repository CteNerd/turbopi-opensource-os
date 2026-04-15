#!/usr/bin/env python3
"""
Update application orchestrator for TurboPi.

This module coordinates the end-to-end update flow:
1. Download (if needed)
2. Verify
3. Install (extract)
4. Atomic symlink switch
5. Restart services
6. Health check
7. Rollback on failure

Follows docs/updater/PROTOCOL.md and docs/updater/RELEASE_INSTALL_LAYOUT.md
"""

import os
import shutil
import subprocess
import logging
from typing import Dict, Optional, Tuple
from download import download_and_verify, DownloadError, ChecksumError
from install import install_release, update_metadata_health_status, InstallError
from health import verify_release_health, log_failed_service_details, TURBOPI_SERVICES


logger = logging.getLogger(__name__)


# Restart only services that should pick up the new release immediately.
# The updater service must not restart itself while orchestrating an update.
UPDATABLE_RUNTIME_SERVICES = [
    'turbopi-api.service',
    'turbopi-ui.service',
]

# Runtime service unit files managed by release updates. The updater service
# itself is included here for unit-file synchronization, but is still excluded
# from restart orchestration while an update is running.
MANAGED_SYSTEMD_UNITS = [
    'turbopi-api.service',
    'turbopi-ui.service',
    'turbopi-updater.service',
]


class UpdateError(Exception):
    """Exception raised when update application fails"""
    pass


class RollbackError(Exception):
    """Exception raised when rollback fails"""
    pass


def sync_systemd_units_from_release(
    release_dir: str,
    systemd_dir: str = '/etc/systemd/system'
) -> Dict[str, Optional[bytes]]:
    """
    Sync managed systemd unit files from a release payload.

    Release payloads may include a `systemd/` directory that contains updated
    service unit files. Existing unit contents are captured for rollback.

    Args:
        release_dir: Installed release directory
        systemd_dir: Systemd unit directory

    Returns:
        Mapping of destination unit path to previous content bytes.
        A value of None means the destination file did not previously exist.

    Raises:
        UpdateError: If copy or daemon-reload fails
    """
    release_systemd_dir = os.path.join(release_dir, 'systemd')
    if not os.path.isdir(release_systemd_dir):
        logger.info("No systemd unit payload in release; skipping unit sync")
        return {}

    logger.info("Syncing systemd unit files from release payload")
    backups: Dict[str, Optional[bytes]] = {}
    copied_units = []

    try:
        for unit_name in MANAGED_SYSTEMD_UNITS:
            src_path = os.path.join(release_systemd_dir, unit_name)
            if not os.path.isfile(src_path):
                continue

            dst_path = os.path.join(systemd_dir, unit_name)
            if dst_path not in backups:
                if os.path.exists(dst_path):
                    with open(dst_path, 'rb') as f:
                        backups[dst_path] = f.read()
                else:
                    backups[dst_path] = None

            shutil.copy2(src_path, dst_path)
            copied_units.append(unit_name)
            logger.info(f"Updated systemd unit: {unit_name}")

        if not copied_units:
            logger.info("No managed unit files found in release payload")
            return {}

        result = subprocess.run(
            ['systemctl', 'daemon-reload'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise UpdateError(f"Failed systemctl daemon-reload: {result.stderr}")

        logger.info("Systemd daemon reloaded after unit sync")
        return backups

    except subprocess.TimeoutExpired:
        raise UpdateError("Timeout during systemd unit synchronization")
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        raise UpdateError(f"Failed syncing systemd units from release: {e}")


def restore_systemd_units(
    backups: Dict[str, Optional[bytes]]
) -> None:
    """
    Restore previously backed up systemd unit files.

    Args:
        backups: Mapping returned by sync_systemd_units_from_release

    Raises:
        RollbackError: If restore or daemon-reload fails
    """
    if not backups:
        return

    logger.warning("Restoring previous systemd unit files for rollback")
    try:
        for dst_path, previous_content in backups.items():
            if previous_content is None:
                if os.path.exists(dst_path):
                    os.remove(dst_path)
            else:
                with open(dst_path, 'wb') as f:
                    f.write(previous_content)

        result = subprocess.run(
            ['systemctl', 'daemon-reload'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RollbackError(f"Failed systemctl daemon-reload: {result.stderr}")

        logger.info("Systemd unit rollback completed")

    except subprocess.TimeoutExpired:
        raise RollbackError("Timeout while restoring systemd units")
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        raise RollbackError(f"Failed restoring systemd units: {e}")


def get_symlink_target(symlink_path: str) -> Optional[str]:
    """
    Get the target of a symlink.
    
    Args:
        symlink_path: Path to the symlink
        
    Returns:
        Target path, or None if symlink doesn't exist or is not a symlink
    """
    if not os.path.islink(symlink_path):
        return None
    
    try:
        return os.readlink(symlink_path)
    except OSError as e:
        logger.error(f"Failed to read symlink {symlink_path}: {e}")
        return None


def atomic_symlink_update(link_path: str, target_path: str) -> None:
    """
    Atomically update a symlink to point to a new target.
    
    Uses ln -sfn for atomic replacement.
    
    Args:
        link_path: Path to the symlink to create/update
        target_path: New target for the symlink
        
    Raises:
        UpdateError: If symlink update fails
    """
    logger.info(f"Updating symlink {link_path} -> {target_path}")
    
    try:
        # Use ln -sfn for atomic symlink update
        # -s: symbolic link
        # -f: force (remove existing)
        # -n: treat destination as normal file if it's a symlink to a directory
        result = subprocess.run(
            ['ln', '-sfn', target_path, link_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise UpdateError(f"Failed to update symlink: {result.stderr}")
        
        logger.info(f"Symlink updated successfully")
        
    except subprocess.TimeoutExpired:
        raise UpdateError(f"Timeout updating symlink {link_path}")
    except Exception as e:
        raise UpdateError(f"Error updating symlink {link_path}: {e}")


def restart_services() -> bool:
    """
    Restart TurboPi services in dependency order.
    
    Services are restarted in order:
    1. turbopi-api.service (base service)
    2. turbopi-ui.service (depends on api)

    The updater service is intentionally excluded to avoid self-termination
    while an update is in progress.
    
    Returns:
        True if all services restarted successfully, False otherwise
    """
    logger.info("Restarting services in dependency order...")
    
    for service in UPDATABLE_RUNTIME_SERVICES:
        logger.info(f"Restarting {service}...")
        try:
            result = subprocess.run(
                ['systemctl', 'restart', service],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to restart {service}: {result.stderr}")
                return False
            
            logger.info(f"Restarted {service} successfully")
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout restarting {service}")
            return False
        except Exception as e:
            logger.error(f"Error restarting {service}: {e}")
            return False
    
    logger.info("All services restarted successfully")
    return True


def switch_to_release(
    new_release_dir: str,
    turbopi_root: str = '/opt/turbopi'
) -> Tuple[Optional[str], Optional[str]]:
    """
    Atomically switch to a new release.
    
    This updates the current and previous symlinks:
    1. Save old previous target
    2. Point previous to current target
    3. Point current to new release
    
    Args:
        new_release_dir: Path to the new release directory
        turbopi_root: Root TurboPi directory (default: /opt/turbopi)
        
    Returns:
        Tuple of (old_current, old_previous) for rollback
        
    Raises:
        UpdateError: If symlink switching fails
    """
    current_link = os.path.join(turbopi_root, 'current')
    previous_link = os.path.join(turbopi_root, 'previous')
    
    # Get current targets for rollback
    old_current = get_symlink_target(current_link)
    old_previous = get_symlink_target(previous_link)
    
    logger.info(f"Switching from release: {old_current}")
    logger.info(f"Switching to release: {new_release_dir}")
    
    # Validate new release exists
    if not os.path.isdir(new_release_dir):
        raise UpdateError(f"New release directory does not exist: {new_release_dir}")
    
    try:
        # Step 1: Update previous to point to current (for rollback)
        if old_current:
            atomic_symlink_update(previous_link, old_current)
        
        # Step 2: Update current to point to new release
        atomic_symlink_update(current_link, new_release_dir)
        
        logger.info("Symlink switch completed successfully")
        return (old_current, old_previous)
        
    except UpdateError:
        logger.error("Failed to switch symlinks")
        raise


def rollback_to_previous(
    old_current: Optional[str],
    old_previous: Optional[str],
    turbopi_root: str = '/opt/turbopi'
) -> None:
    """
    Rollback to the previous release.
    
    This restores the symlinks to their pre-update state.
    
    Args:
        old_current: Previous current target (for rollback)
        old_previous: Previous previous target (for rollback chain)
        turbopi_root: Root TurboPi directory (default: /opt/turbopi)
        
    Raises:
        RollbackError: If rollback fails
    """
    logger.warning("Rolling back to previous release")
    
    current_link = os.path.join(turbopi_root, 'current')
    previous_link = os.path.join(turbopi_root, 'previous')
    
    if not old_current:
        raise RollbackError("Cannot rollback: no previous release available")
    
    try:
        # Restore current to old_current
        atomic_symlink_update(current_link, old_current)
        
        # Restore previous to old_previous (maintains rollback chain)
        if old_previous:
            atomic_symlink_update(previous_link, old_previous)
        
        logger.info(f"Rolled back to: {old_current}")
        
    except UpdateError as e:
        raise RollbackError(f"Rollback failed: {e}")


def apply_update(
    version: str,
    download_url: str,
    checksum: str,
    download_dir: str = '/opt/turbopi/downloads',
    releases_base: str = '/opt/turbopi/releases',
    turbopi_root: str = '/opt/turbopi',
    requires_reboot: bool = False,
    skip_download: bool = False
) -> bool:
    """
    Apply a complete update to the system.
    
    This orchestrates the full update flow:
    1. Download and verify (if not skipped)
    2. Install to releases/<version>
    3. Atomic symlink switch
    4. Restart services
    5. Health check
    6. Rollback on failure
    
    Args:
        version: Version to install (e.g., "0.1.0")
        download_url: URL to download from
        checksum: Expected SHA256 checksum
        download_dir: Directory for downloads (default: /opt/turbopi/downloads)
        releases_base: Base directory for releases (default: /opt/turbopi/releases)
        turbopi_root: Root TurboPi directory (default: /opt/turbopi)
        requires_reboot: Whether this update requires a reboot
        skip_download: Skip download if tarball already exists
        
    Returns:
        True if update succeeded, False if failed and rolled back
        
    Raises:
        UpdateError: If update fails and cannot rollback
    """
    logger.info(f"=== Starting update to version {version} ===")
    
    # Track state for rollback
    old_current = None
    old_previous = None
    new_release_dir = None
    tarball_path = None
    systemd_unit_backups: Dict[str, Optional[bytes]] = {}
    
    try:
        # Step 1: Download and verify
        version_download_dir = os.path.join(download_dir, version)
        tarball_path = os.path.join(version_download_dir, f"turbopi-{version}.tar.gz")
        
        if skip_download and os.path.exists(tarball_path):
            logger.info(f"Skipping download, using existing tarball: {tarball_path}")
        else:
            logger.info("Step 1: Download and verify")
            download_and_verify(download_url, tarball_path, checksum)
        
        # Step 2: Install (extract)
        logger.info("Step 2: Install release")
        new_release_dir = install_release(
            tarball_path,
            version,
            releases_base,
            source_url=download_url,
            checksum=checksum,
            requires_reboot=requires_reboot
        )
        
        # Step 3: Atomic symlink switch
        logger.info("Step 3: Switch symlinks")
        old_current, old_previous = switch_to_release(new_release_dir, turbopi_root)

        # Step 4: Sync systemd unit files (if provided in release payload)
        logger.info("Step 4: Sync systemd units")
        systemd_unit_backups = sync_systemd_units_from_release(new_release_dir)
        
        # Step 5: Restart services
        logger.info("Step 5: Restart services")
        if not restart_services():
            raise UpdateError("Failed to restart services")
        
        # Step 6: Health check
        logger.info("Step 6: Health check")
        if not verify_release_health(timeout=60):
            raise UpdateError("Health check failed")
        
        # Step 7: Update metadata with health status
        logger.info("Step 7: Update metadata")
        update_metadata_health_status(new_release_dir, passed=True)
        
        # Success!
        logger.info(f"=== Update to version {version} completed successfully ===")
        
        # Note about reboot if required
        if requires_reboot:
            logger.warning(f"!!! REBOOT REQUIRED for version {version} !!!")
            logger.warning("Please reboot the system to complete the update")
        
        return True
        
    except (DownloadError, ChecksumError) as e:
        logger.error(f"Download/verification failed: {e}")
        logger.error("Update aborted - no changes made to system")
        return False
        
    except InstallError as e:
        logger.error(f"Installation failed: {e}")
        logger.error("Update aborted - no changes made to system")
        return False
        
    except UpdateError as e:
        logger.error(f"Update failed: {e}")
        
        # Attempt rollback if we switched symlinks
        if old_current:
            logger.warning("Attempting rollback to previous version")
            try:
                rollback_to_previous(old_current, old_previous, turbopi_root)

                # Restore systemd units that were replaced by this update.
                restore_systemd_units(systemd_unit_backups)
                
                # Restart services with old version
                logger.info("Restarting services with previous version")
                if not restart_services():
                    raise RollbackError("Failed to restart services after rollback")
                
                # Verify rollback health
                logger.info("Verifying rollback health")
                if verify_release_health(timeout=60):
                    logger.info("Rollback completed successfully")
                    
                    # Mark failed release in metadata
                    if new_release_dir:
                        try:
                            update_metadata_health_status(new_release_dir, passed=False)
                        except (InstallError, OSError) as meta_err:
                            # Best effort - don't fail rollback if metadata update fails
                            logger.warning(f"Failed to update metadata for failed release: {meta_err}")
                    
                    return False
                else:
                    raise RollbackError("Health check failed after rollback")
                    
            except RollbackError as rb_err:
                logger.critical(f"ROLLBACK FAILED: {rb_err}")
                logger.critical("System may be in inconsistent state!")
                logger.critical("Manual intervention required")
                
                # Log service details for debugging
                for service in TURBOPI_SERVICES:
                    log_failed_service_details(service)
                
                raise UpdateError(f"Update failed and rollback failed: {rb_err}")
        else:
            # No rollback needed, update failed before switching
            logger.error("Update failed before symlink switch - no rollback needed")
            return False
    
    except (KeyboardInterrupt, SystemExit):
        # Let interrupts and system exits propagate
        logger.warning("Update interrupted by user or system")
        raise
    
    except Exception as e:
        logger.critical(f"Unexpected error during update: {e}")
        logger.critical("Update aborted")
        raise UpdateError(f"Unexpected error: {e}")
