#!/usr/bin/env python3
"""
TurboPi API Backend Service (Skeleton)

This is a minimal skeleton implementation that provides:
- Health endpoint at /health
- Basic logging
- Configuration loading from environment variables
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone


def get_current_version() -> str:
    """
    Get the current version from environment variable.
    
    Returns:
        Current version string from VERSION env var, defaults to '0.1.0-dev'
    """
    return os.environ.get('VERSION', '0.1.0-dev')


def normalize_version(version: str) -> tuple:
    """
    Normalize a version string to a tuple for comparison.
    
    Handles versions like '0.1.0', '0.1.0-dev', 'v0.1.0'
    
    Args:
        version: Version string to normalize
        
    Returns:
        Tuple of (major, minor, patch) integers
    """
    # Remove 'v' prefix if present
    version = version.lstrip('v')
    
    # Remove pre-release suffix (e.g., '-dev', '-alpha', '-beta')
    version = version.split('-')[0]
    
    # Split into parts
    parts = version.split('.')
    
    # Convert to integers, pad with zeros if needed
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, IndexError):
        # If parsing fails, return (0, 0, 0)
        return (0, 0, 0)


def is_newer_version(current: str, latest: str) -> bool:
    """
    Compare two version strings to determine if latest is newer than current.
    
    Args:
        current: Current version string
        latest: Latest version string
        
    Returns:
        True if latest is newer than current, False otherwise
    """
    current_tuple = normalize_version(current)
    latest_tuple = normalize_version(latest)
    return latest_tuple > current_tuple


def fetch_latest_stable_release() -> Optional[dict]:
    """
    Fetch the latest stable release information from GitHub API.
    
    Returns:
        Dictionary with 'version' and 'url' keys, or None if fetch fails
        or if essential fields are missing from the response
    """
    github_api_url = "https://api.github.com/repos/CteNerd/turbopi-opensource-os/releases/latest"
    
    try:
        # GitHub API requires a User-Agent header
        req = urllib.request.Request(github_api_url)
        req.add_header('User-Agent', 'TurboPi-UpdateChecker/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            # Extract version from tag_name (e.g., "v0.1.0" -> "0.1.0")
            tag_name = data.get('tag_name', '')
            if not tag_name:
                # Missing essential field - return None for consistency
                logging.error("GitHub API response missing 'tag_name' field")
                return None
            
            version = tag_name.lstrip('v')
            
            # Find the release artifact URL (tar.gz file)
            assets = data.get('assets', [])
            url = None
            for asset in assets:
                # Use defensive programming to handle missing fields
                asset_name = asset.get('name', '')
                if asset_name.endswith('.tar.gz'):
                    url = asset.get('browser_download_url')
                    if url:
                        break
            
            # If no asset found, use tarball_url as fallback
            if not url:
                url = data.get('tarball_url', '')
            
            return {
                'version': version,
                'url': url
            }
    except urllib.error.HTTPError as e:
        logging.error(f"HTTP error fetching latest release: {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        logging.error(f"Network error fetching latest release: {e.reason}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logging.error(f"Error parsing release data: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching latest release: {e}")
        return None


class APIHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for the API service"""

    def log_message(self, format, *args):
        """Override to log to stdout instead of stderr"""
        sys.stdout.write("%s - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.handle_health()
        elif self.path == '/system/version':
            self.handle_system_version()
        elif self.path == '/updates/check':
            self.handle_updates_check()
        else:
            self.send_error(404, "Not Found")

    def handle_health(self):
        """Handle /health endpoint"""
        try:
            # Get system uptime
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.readline().split()[0])

            # Get CPU temperature (if available)
            cpu_temp = None
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
            except (FileNotFoundError, ValueError):
                # CPU temperature not available on this system
                pass

            # Get version from environment or default
            version = get_current_version()

            health_data = {
                'status': 'ok',
                'uptime': uptime,
                'cpu_temp': cpu_temp,
                'version': version,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode())
        except Exception as e:
            # Log the detailed error internally
            logging.error(f"Health endpoint error: {str(e)}")
            # Return generic error message to client
            self.send_error(500, "Internal Server Error: Unable to retrieve health status")

    def handle_system_version(self):
        """Handle /system/version endpoint"""
        try:
            current_version = get_current_version()
            
            # Try to fetch latest stable release
            latest_release = fetch_latest_stable_release()
            latest_stable = latest_release['version'] if latest_release else None
            
            version_data = {
                'current': current_version,
                'latest_stable': latest_stable
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(version_data).encode())
            
        except Exception as e:
            logging.error(f"System version endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to retrieve version information")

    def handle_updates_check(self):
        """Handle /updates/check endpoint"""
        try:
            current_version = get_current_version()
            
            # Fetch latest stable release
            latest_release = fetch_latest_stable_release()
            
            if latest_release:
                latest_version = latest_release['version']
                update_available = is_newer_version(current_version, latest_version)
            else:
                # If we can't fetch the latest release, return unavailable
                latest_version = None
                update_available = False
            
            updates_data = {
                'update_available': update_available,
                'latest_version': latest_version
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(updates_data).encode())
            
        except Exception as e:
            logging.error(f"Updates check endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to check for updates")


def main():
    """Main entry point for the API service"""
    # Configure logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Load configuration from environment
    host = os.environ.get('API_HOST', '0.0.0.0')
    
    # Validate and parse port
    try:
        port = int(os.environ.get('API_PORT', '8080'))
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
    except ValueError as e:
        logging.error(f"Invalid API_PORT configuration: {e}")
        sys.exit(1)
    
    robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')

    logging.info(f"TurboPi API Backend starting...")
    logging.info(f"Robot Name: {robot_name}")
    logging.info(f"Listening on {host}:{port}")
    logging.info(f"Health endpoint: http://{host}:{port}/health")

    # Create and start HTTP server
    server = HTTPServer((host, port), APIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("\nShutting down API service...")
        server.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
