#!/usr/bin/env python3
"""
Download and verification module for TurboPi updates.

This module handles:
- Artifact download from release URLs
- SHA256 checksum verification
- Safe failure handling
- URL redaction for secure logging (removes credentials and query parameters)

Security Notes:
- All URLs are redacted before logging to prevent credential leakage
- Only public URLs without authentication should be used for downloads
"""

import os
import hashlib
import logging
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlunparse


logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when download fails"""
    pass


class ChecksumError(Exception):
    """Exception raised when checksum verification fails"""
    pass


def _redact_url(url: str) -> str:
    """
    Redact sensitive information from URLs for safe logging.
    
    Removes query parameters and authentication credentials to prevent
    leaking secrets in logs.
    
    Args:
        url: Original URL that may contain sensitive information
        
    Returns:
        Redacted URL safe for logging (without query params and credentials)
    """
    try:
        parsed = urlparse(url)
        # Build netloc without credentials, preserving hostname and port
        if parsed.hostname:
            netloc = parsed.hostname
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
        else:
            # Fallback: strip credentials from netloc if hostname not available
            netloc = parsed.netloc.split('@')[-1] if '@' in parsed.netloc else parsed.netloc
        
        # Remove username, password, and query parameters
        redacted = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            '',  # Remove params
            '',  # Remove query
            ''   # Remove fragment
        ))
        return redacted
    except Exception:
        # If URL parsing fails, return a safe placeholder
        return "<url-redacted>"


def download_file(url: str, destination: str, timeout: int = 300) -> None:
    """
    Download a file from URL to destination path.
    
    URLs are automatically redacted in logs to prevent credential leakage.
    Use only public URLs without authentication for downloads.
    
    Args:
        url: URL to download from (credentials/query params redacted in logs)
        destination: Local file path to save to
        timeout: Download timeout in seconds (default: 300)
        
    Raises:
        DownloadError: If download fails
    """
    logger.info(f"Downloading from {_redact_url(url)}")
    logger.info(f"Saving to {destination}")
    
    # Create destination directory if it doesn't exist
    destination_dir = os.path.dirname(destination)
    if destination_dir:
        os.makedirs(destination_dir, exist_ok=True)
    
    try:
        # Download with progress tracking
        with urllib.request.urlopen(url, timeout=timeout) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            last_logged = 0
            
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Log progress every 1MB
                    if downloaded - last_logged >= (1024 * 1024):
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}% ({downloaded}/{total_size} bytes)")
                        else:
                            logger.info(f"Downloaded: {downloaded} bytes")
                        last_logged = downloaded
            
            logger.info(f"Download complete: {downloaded} bytes")
            
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP error downloading {_redact_url(url)}: {e.code} {e.reason}"
        logger.error(error_msg)
        raise DownloadError(error_msg) from e
        
    except urllib.error.URLError as e:
        error_msg = f"Network error downloading {_redact_url(url)}: {e.reason}"
        logger.error(error_msg)
        raise DownloadError(error_msg) from e
        
    except OSError as e:
        error_msg = f"File system error saving to {destination}: {e}"
        logger.error(error_msg)
        raise DownloadError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Unexpected error downloading {_redact_url(url)}: {e}"
        logger.error(error_msg)
        raise DownloadError(error_msg) from e


def calculate_sha256(file_path: str) -> str:
    """
    Calculate SHA256 checksum of a file.
    
    Args:
        file_path: Path to file to checksum
        
    Returns:
        Hexadecimal SHA256 checksum string
        
    Raises:
        DownloadError: If file cannot be read
    """
    logger.info(f"Calculating SHA256 checksum for {file_path}")
    
    try:
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        logger.info(f"Calculated checksum: {checksum}")
        return checksum
        
    except OSError as e:
        error_msg = f"Error reading file {file_path}: {e}"
        logger.error(error_msg)
        raise DownloadError(error_msg) from e


def verify_checksum(file_path: str, expected_checksum: str) -> None:
    """
    Verify that file matches expected SHA256 checksum.
    
    Args:
        file_path: Path to file to verify
        expected_checksum: Expected SHA256 checksum (hex string)
        
    Raises:
        ChecksumError: If checksum doesn't match
        DownloadError: If file cannot be read
    """
    logger.info(f"Verifying checksum for {file_path}")
    logger.info(f"Expected checksum: {expected_checksum}")
    
    # Normalize checksum format (remove "sha256:" prefix if present)
    if expected_checksum.startswith("sha256:"):
        expected_checksum = expected_checksum[7:]
    
    expected_checksum = expected_checksum.lower().strip()
    
    actual_checksum = calculate_sha256(file_path)
    
    if actual_checksum != expected_checksum:
        error_msg = f"Checksum mismatch for {file_path}: expected {expected_checksum}, got {actual_checksum}"
        logger.error(error_msg)
        raise ChecksumError(error_msg)
    
    logger.info(f"Checksum verification PASSED for {file_path}")


def download_and_verify(url: str, destination: str, expected_checksum: str, 
                       timeout: int = 300) -> None:
    """
    Download a file and verify its checksum.
    
    This is the main function for secure artifact download.
    If checksum verification fails, the downloaded file is removed.
    
    Args:
        url: URL to download from
        destination: Local file path to save to
        expected_checksum: Expected SHA256 checksum
        timeout: Download timeout in seconds (default: 300)
        
    Raises:
        DownloadError: If download fails
        ChecksumError: If checksum verification fails
    """
    logger.info(f"Starting download and verification from {_redact_url(url)}")
    
    try:
        # Download the file
        download_file(url, destination, timeout)
        
        # Verify checksum
        verify_checksum(destination, expected_checksum)
        
        logger.info(f"Download and verification successful: {destination}")
        
    except ChecksumError:
        # Clean up invalid file
        logger.warning(f"Removing file with invalid checksum: {destination}")
        try:
            if os.path.exists(destination):
                os.remove(destination)
                logger.info(f"Removed invalid file: {destination}")
        except OSError as e:
            logger.error(f"Failed to remove invalid file {destination}: {e}")
        
        # Re-raise the checksum error
        raise
    
    except DownloadError:
        # Clean up partial download
        logger.warning(f"Removing partial download: {destination}")
        try:
            if os.path.exists(destination):
                os.remove(destination)
                logger.info(f"Removed partial download: {destination}")
        except OSError as e:
            logger.error(f"Failed to remove partial download {destination}: {e}")
        
        # Re-raise the download error
        raise
