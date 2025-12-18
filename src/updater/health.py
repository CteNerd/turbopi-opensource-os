#!/usr/bin/env python3
"""
Health check module for TurboPi updates.

This module handles:
- Verification that services are running after update
- Basic health status checking
- Service availability validation

Follows docs/updater/PROTOCOL.md health check requirements.
"""

import os
import subprocess
import time
import logging
from typing import List, Dict, Optional


logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Exception raised when health check fails"""
    pass


def check_service_status(service_name: str) -> bool:
    """
    Check if a systemd service is active and running.
    
    Args:
        service_name: Name of the systemd service (e.g., 'turbopi-api.service')
        
    Returns:
        True if service is active, False otherwise
    """
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        is_active = result.stdout.strip() == 'active'
        
        if is_active:
            logger.info(f"Service {service_name} is active")
        else:
            logger.warning(f"Service {service_name} is not active: {result.stdout.strip()}")
        
        return is_active
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout checking service {service_name}")
        return False
    except Exception as e:
        logger.error(f"Error checking service {service_name}: {e}")
        return False


def wait_for_service(service_name: str, timeout: int = 30, poll_interval: int = 2) -> bool:
    """
    Wait for a service to become active within timeout period.
    
    Args:
        service_name: Name of the systemd service
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
        
    Returns:
        True if service became active, False if timeout
    """
    logger.info(f"Waiting for service {service_name} (timeout: {timeout}s)")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if check_service_status(service_name):
            elapsed = time.time() - start_time
            logger.info(f"Service {service_name} became active after {elapsed:.1f}s")
            return True
        
        time.sleep(poll_interval)
    
    logger.error(f"Service {service_name} did not become active within {timeout}s")
    return False


def check_all_services(timeout_per_service: int = 30) -> Dict[str, bool]:
    """
    Check all TurboPi services are running.
    
    Args:
        timeout_per_service: Max time to wait for each service
        
    Returns:
        Dictionary mapping service names to their status (True = healthy)
    """
    services = [
        'turbopi-api.service',
        'turbopi-ui.service',
        'turbopi-updater.service'
    ]
    
    results = {}
    
    for service in services:
        # Wait for service to become active
        results[service] = wait_for_service(service, timeout=timeout_per_service)
    
    return results


def verify_release_health(timeout: int = 60) -> bool:
    """
    Verify that all TurboPi services are healthy after an update.
    
    This is the main health check function called after applying an update.
    
    Args:
        timeout: Maximum time to wait for all services (divided among services)
        
    Returns:
        True if all services are healthy, False otherwise
    """
    logger.info("Starting post-update health check")
    
    # Give services time to start
    logger.info("Waiting 5 seconds for services to initialize...")
    time.sleep(5)
    
    # Check all services
    timeout_per_service = max(10, timeout // 3)  # Divide timeout among services
    results = check_all_services(timeout_per_service)
    
    # Evaluate results
    all_healthy = all(results.values())
    
    if all_healthy:
        logger.info("Health check PASSED - all services are healthy")
    else:
        logger.error("Health check FAILED - some services are unhealthy:")
        for service, status in results.items():
            status_str = "✓ HEALTHY" if status else "✗ UNHEALTHY"
            logger.error(f"  {service}: {status_str}")
    
    return all_healthy


def get_service_logs(service_name: str, lines: int = 50) -> Optional[str]:
    """
    Get recent log lines from a service for debugging.
    
    Args:
        service_name: Name of the systemd service
        lines: Number of recent log lines to retrieve
        
    Returns:
        Log output as string, or None if unavailable
    """
    try:
        result = subprocess.run(
            ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            logger.warning(f"Failed to get logs for {service_name}: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout getting logs for {service_name}")
        return None
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return None


def log_failed_service_details(service_name: str) -> None:
    """
    Log detailed information about a failed service for debugging.
    
    Args:
        service_name: Name of the failed service
    """
    logger.error(f"=== Details for failed service: {service_name} ===")
    
    # Get service status
    try:
        result = subprocess.run(
            ['systemctl', 'status', service_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        logger.error(f"Service status:\n{result.stdout}")
    except Exception as e:
        logger.error(f"Could not get service status: {e}")
    
    # Get recent logs
    logs = get_service_logs(service_name, lines=30)
    if logs:
        logger.error(f"Recent logs:\n{logs}")
    
    logger.error(f"=== End details for {service_name} ===")
