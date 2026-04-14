#!/usr/bin/env python3
"""
TurboPi Update Service (Skeleton)

This is a minimal skeleton implementation that provides:
- Background service for update management
- Basic logging
- Configuration loading from environment variables
- Download and verification support
"""

import os
import sys
import time
import signal
import logging
import json
import re

# Import download and verification functionality
try:
    from download import download_and_verify, DownloadError, ChecksumError, redact_url
    from apply import apply_update, UpdateError
except ImportError:
    # Fallback if running in standalone mode without proper imports
    download_and_verify = None
    apply_update = None
    DownloadError = Exception
    ChecksumError = Exception
    UpdateError = Exception
    redact_url = lambda url: url  # Simple passthrough if import fails


class UpdaterService:
    """Minimal updater service implementation"""

    def __init__(self):
        self.running = True
        self.robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')
        self.auto_update = os.environ.get('AUTO_UPDATE', 'false').lower() == 'true'
        self.auto_update_channel = self._validate_auto_update_channel(
            os.environ.get('AUTO_UPDATE_CHANNEL', 'stable')
        )
        self.auto_update_schedule_utc = self._validate_schedule_utc(
            os.environ.get('AUTO_UPDATE_SCHEDULE_UTC', '03:00')
        )
        self.download_dir = os.environ.get('DOWNLOAD_DIR', '/opt/turbopi/downloads')
        self.trigger_dir = os.environ.get('TRIGGER_DIR', '/var/lib/turbopi')
        self.trigger_file = os.path.join(self.trigger_dir, 'update-trigger.json')
        
        # Configurable polling interval with validation
        poll_interval_raw = os.environ.get('UPDATER_POLL_INTERVAL', '10')
        try:
            self.poll_interval = int(poll_interval_raw)
            if self.poll_interval < 1:
                raise ValueError("poll interval must be positive")
        except ValueError:
            logging.warning(
                "Invalid UPDATER_POLL_INTERVAL '%s', falling back to default of 10 seconds",
                poll_interval_raw,
            )
            self.poll_interval = 10
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    @staticmethod
    def _validate_auto_update_channel(channel_raw: str) -> str:
        channel = (channel_raw or 'stable').strip().lower()
        if channel != 'stable':
            logging.warning(
                "Invalid AUTO_UPDATE_CHANNEL '%s'; only 'stable' is supported. Falling back to 'stable'.",
                channel_raw,
            )
            return 'stable'
        return channel

    @staticmethod
    def _validate_schedule_utc(schedule_raw: str) -> str:
        schedule = (schedule_raw or '03:00').strip()
        if re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', schedule):
            return schedule
        logging.warning(
            "Invalid AUTO_UPDATE_SCHEDULE_UTC '%s'; expected HH:MM 24-hour UTC. Falling back to 03:00.",
            schedule_raw,
        )
        return '03:00'

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down updater service...")
        self.running = False
    
    def download_update(self, url: str, version: str, expected_checksum: str) -> bool:
        """
        Download and verify an update artifact.
        
        This implements the download and verification steps from docs/updater/PROTOCOL.md:
        - Download artifact + checksum
        - Verify checksum
        - Reject invalid checksums
        - Fail safely
        
        URLs are automatically redacted in logs to prevent credential leakage.
        
        Args:
            url: URL to download the update artifact from (redacted in logs)
            version: Version string for the update (e.g., "0.1.0")
            expected_checksum: Expected SHA256 checksum
            
        Returns:
            True if download and verification succeeded, False otherwise
        """
        if download_and_verify is None:
            logging.error("Download functionality not available")
            return False
        
        try:
            # Determine destination path
            dest_dir = os.path.join(self.download_dir, version)
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, f"turbopi-{version}.tar.gz")
            
            logging.info(f"Starting update download for version {version}")
            logging.info(f"Download URL: {redact_url(url)}")
            logging.info(f"Destination: {dest_file}")
            
            # Download and verify
            download_and_verify(url, dest_file, expected_checksum)
            
            logging.info(f"Update download and verification successful for version {version}")
            return True
            
        except ChecksumError as e:
            logging.error(f"Checksum verification failed for version {version}: {e}")
            logging.error("Invalid checksum prevents install - update rejected")
            return False
            
        except DownloadError as e:
            logging.error(f"Download failed for version {version}: {e}")
            logging.error("Download error prevents install - update rejected")
            return False
            
        except Exception as e:
            logging.error(f"Unexpected error downloading version {version}: {e}")
            logging.error("Unexpected error prevents install - update rejected")
            return False
    
    def apply_update_to_system(
        self,
        version: str,
        url: str,
        checksum: str,
        requires_reboot: bool = False
    ) -> bool:
        """
        Apply a complete update to the system.
        
        This orchestrates the full update flow from docs/updater/PROTOCOL.md:
        1. Download and verify
        2. Extract to releases/<version>
        3. Atomic symlink switch
        4. Restart services
        5. Health check
        6. Rollback on failure
        
        Args:
            version: Version to install (e.g., "0.1.0")
            url: URL to download from (redacted in logs)
            checksum: Expected SHA256 checksum
            requires_reboot: Whether this update requires a reboot
            
        Returns:
            True if update succeeded, False if failed or rolled back
        """
        if apply_update is None:
            logging.error("Update orchestration functionality not available")
            return False
        
        logging.info(f"Applying update to version {version}")
        logging.info(f"Download URL: {redact_url(url)}")
        logging.info(f"Requires reboot: {requires_reboot}")
        
        try:
            result = apply_update(
                version=version,
                download_url=url,
                checksum=checksum,
                download_dir=self.download_dir,
                requires_reboot=requires_reboot
            )
            
            if result:
                logging.info(f"Update to version {version} completed successfully")
                if requires_reboot:
                    logging.warning("!!! REBOOT REQUIRED !!!")
                    logging.warning("Please reboot the system to complete the update")
            else:
                logging.error(f"Update to version {version} failed")
            
            return result
            
        except UpdateError as e:
            logging.critical(f"Update failed with error: {e}")
            logging.critical("System may require manual intervention")
            return False
            
        except Exception as e:
            logging.critical(f"Unexpected error during update: {e}")
            logging.critical("Update aborted")
            return False

    def check_for_update_trigger(self) -> bool:
        """
        Check if there's an update trigger file and process it.
        
        Uses atomic rename to prevent race conditions during processing.
        
        Returns:
            True if an update was triggered and processed, False otherwise
        """
        if not os.path.exists(self.trigger_file):
            return False
        
        # Atomically move trigger file to processing location to prevent race conditions
        processing_file = self.trigger_file + '.processing'
        
        try:
            # Rename trigger file atomically
            os.rename(self.trigger_file, processing_file)
        except OSError:
            # File doesn't exist or already being processed
            return False
        
        try:
            # Read processing file
            with open(processing_file, 'r') as f:
                trigger_data = json.load(f)
            
            version = trigger_data.get('version')
            url = trigger_data.get('url')
            checksum = trigger_data.get('checksum')
            
            # Check for missing fields and log which ones
            missing_fields = []
            if not version:
                missing_fields.append("version")
            if not url:
                missing_fields.append("url")
            if not checksum:
                missing_fields.append("checksum")
            if missing_fields:
                logging.error(
                    "Invalid trigger file: missing required fields: %s",
                    ", ".join(missing_fields),
                )
                return False
            
            logging.info(f"Found update trigger for version {version}")
            
            # Process the update
            success = self.apply_update_to_system(
                version=version,
                url=url,
                checksum=checksum,
                requires_reboot=False  # Will be determined from release metadata
            )
            
            return success
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse trigger file: {e}")
            return False
        except OSError as e:
            logging.error(f"Failed to read trigger file: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error processing trigger: {e}")
            return False
        finally:
            # Always remove processing file to prevent accumulation
            try:
                if os.path.exists(processing_file):
                    os.remove(processing_file)
            except OSError as e:
                logging.debug(f"Failed to remove processing file {processing_file}: {e}")
    
    def run(self):
        """Main service loop"""
        logging.info(f"TurboPi Updater Service starting...")
        logging.info(f"Robot Name: {self.robot_name}")
        logging.info(f"Auto Update: {self.auto_update}")
        logging.info(f"Auto Update Channel: {self.auto_update_channel}")
        logging.info(f"Auto Update Schedule (UTC): {self.auto_update_schedule_utc}")
        logging.info(f"Poll Interval: {self.poll_interval}s")
        logging.info(f"Service running in background mode...")
        logging.info(f"Updater service: READY - waiting for update requests")

        # Main service loop - runs indefinitely until shutdown
        check_count = 0
        while self.running:
            # Check for update trigger file
            if self.check_for_update_trigger():
                logging.info("Update trigger processed")
            
            # Sleep before next check
            time.sleep(self.poll_interval)
            check_count += 1
            # Log every 10 minutes (adjust based on poll interval)
            log_interval = max(1, int(600 / self.poll_interval))
            if check_count % log_interval == 0:
                logging.info(f"Updater service: RUNNING - check #{check_count} completed")

        logging.info("Updater service: STOPPED")


def main():
    """Main entry point for the updater service"""
    # Configure logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    service = UpdaterService()
    service.run()


if __name__ == '__main__':
    main()
