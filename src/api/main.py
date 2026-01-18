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
import threading
import re
from typing import Optional, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

# Import wake word engine (add path for imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'voice'))
try:
    from wake_word import WakeWordEngine
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False
    # Note: This warning is logged before logging.basicConfig() in main()
    # It will use default logging configuration (stderr) but this is acceptable
    # as it only occurs during module import if wake_word is not available
    logging.warning("Wake word engine not available")


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


def fetch_latest_stable_release() -> Optional[Dict]:
    """
    Fetch the latest stable release information from GitHub API.
    
    Returns:
        Dictionary with 'version', 'url', and 'checksum' keys, or None if fetch fails
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
            
            # Find the release artifact URL (tar.gz file) and checksum
            assets = data.get('assets', [])
            url = None
            checksum = None
            
            for asset in assets:
                # Use defensive programming to handle missing fields
                asset_name = asset.get('name', '')
                if asset_name.endswith('.tar.gz') and not asset_name.endswith('.sha256'):
                    url = asset.get('browser_download_url')
                elif asset_name.endswith('.tar.gz.sha256'):
                    # Found checksum file, download and parse it
                    checksum_url = asset.get('browser_download_url')
                    if checksum_url:
                        try:
                            checksum_req = urllib.request.Request(checksum_url)
                            checksum_req.add_header('User-Agent', 'TurboPi-UpdateChecker/1.0')
                            with urllib.request.urlopen(checksum_req, timeout=10) as checksum_response:
                                checksum_content = checksum_response.read().decode().strip()
                                # Extract checksum (format: "checksum filename" or just "checksum")
                                if checksum_content:
                                    candidate_checksum = checksum_content.split()[0]
                                    # Validate that it's a valid SHA256 checksum (64 hex characters)
                                    if re.fullmatch(r'[a-fA-F0-9]{64}', candidate_checksum):
                                        checksum = candidate_checksum.lower()
                                    else:
                                        logging.warning(
                                            "Checksum file content does not contain a valid SHA256 checksum"
                                        )
                        except Exception as e:
                            logging.warning(f"Failed to fetch checksum file: {e}")
            
            # If no asset found, use tarball_url as fallback
            if not url:
                url = data.get('tarball_url', '')
            
            # Try to extract checksum from release body if not found in assets
            if not checksum:
                body = data.get('body', '')
                # Look for SHA256 checksum patterns in release notes
                # Common formats: "sha256: abc123..." or "SHA256: abc123..."
                checksum_match = re.search(r'(?:sha256|SHA256):\s*([a-fA-F0-9]{64})', body)
                if checksum_match:
                    checksum = checksum_match.group(1).lower()
            
            return {
                'version': version,
                'url': url,
                'checksum': checksum
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


def trigger_system_update(version: str, url: str, checksum: str) -> None:
    """
    Trigger a system update asynchronously via trigger file IPC.
    
    This function creates a trigger file that the updater service polls for.
    The updater service detects the file and initiates the update process.
    
    Args:
        version: Version to install
        url: Download URL
        checksum: SHA256 checksum
    """
    try:
        logging.info(f"Triggering update to version {version}")
        
        # Create a trigger file with update details that the updater service can read
        # Use environment variable for consistency with updater service
        trigger_dir = os.environ.get('TRIGGER_DIR', '/var/lib/turbopi')
        os.makedirs(trigger_dir, exist_ok=True)
        
        trigger_file = os.path.join(trigger_dir, 'update-trigger.json')
        tmp_trigger_file = trigger_file + '.tmp'
        trigger_data = {
            'version': version,
            'url': url,
            'checksum': checksum,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Write to a temporary file and atomically rename into place so the updater
        # never observes a partially-written trigger file.
        with open(tmp_trigger_file, 'w') as f:
            json.dump(trigger_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(tmp_trigger_file, trigger_file)
        
        logging.info(f"Update trigger file created: {trigger_file}")
        logging.info("Update will be processed by turbopi-updater service")
        
    except Exception as e:
        logging.error(f"Failed to trigger update: {e}")


class APIHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for the API service"""
    
    # Global wake word engine instance (shared across requests)
    _wake_word_engine: Optional['WakeWordEngine'] = None
    _wake_word_lock = threading.Lock()
    
    @classmethod
    def get_wake_word_engine(cls):
        """Get or create wake word engine instance (singleton pattern)"""
        if not WAKE_WORD_AVAILABLE:
            return None
        
        with cls._wake_word_lock:
            if cls._wake_word_engine is None:
                cls._wake_word_engine = WakeWordEngine()
                logging.info("Wake word engine initialized")
            return cls._wake_word_engine

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
        elif self.path == '/voice/wake-word/status':
            self.handle_wake_word_status()
        elif self.path == '/voice/wake-word/config':
            self.handle_wake_word_get_config()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/updates/apply':
            self.handle_updates_apply()
        elif self.path == '/voice/wake-word/config':
            self.handle_wake_word_update_config()
        elif self.path == '/voice/stt':
            self.handle_stt()
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
    
    def handle_updates_apply(self):
        """Handle /updates/apply endpoint"""
        try:
            current_version = get_current_version()
            
            # Fetch latest stable release with checksum
            latest_release = fetch_latest_stable_release()
            
            if not latest_release:
                self.send_error(500, "Failed to fetch latest release information")
                return
            
            latest_version = latest_release['version']
            download_url = latest_release['url']
            checksum = latest_release.get('checksum')
            
            # Validate we have all required information
            if not download_url:
                self.send_error(500, "No download URL available for latest release")
                return
            
            if not checksum:
                self.send_error(500, "No checksum available for latest release - cannot verify integrity")
                return
            
            # Check if update is needed
            if not is_newer_version(current_version, latest_version):
                response_data = {
                    'status': 'no_update_needed',
                    'message': f'Already running latest version {current_version}'
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                return
            
            # Trigger update asynchronously
            logging.info(f"Starting update from {current_version} to {latest_version}")
            
            # Start update in background thread
            update_thread = threading.Thread(
                target=trigger_system_update,
                args=(latest_version, download_url, checksum),
                daemon=True
            )
            update_thread.start()
            
            # Return 202 Accepted immediately
            response_data = {
                'status': 'update_started',
                'message': f'Update to version {latest_version} has been initiated',
                'version': latest_version
            }
            
            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
            logging.info(f"Update request accepted for version {latest_version}")
            
        except Exception as e:
            logging.error(f"Updates apply endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to apply update")
    
    def handle_wake_word_status(self):
        """Handle GET /voice/wake-word/status endpoint"""
        try:
            engine = self.get_wake_word_engine()
            if engine is None:
                self.send_error(503, "Wake word engine not available")
                return
            
            status = engine.get_status()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
            
        except Exception as e:
            logging.error(f"Wake word status endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to get wake word status")
    
    def handle_wake_word_get_config(self):
        """Handle GET /voice/wake-word/config endpoint"""
        try:
            engine = self.get_wake_word_engine()
            if engine is None:
                self.send_error(503, "Wake word engine not available")
                return
            
            config = engine.get_config()
            config_data = {
                'wake_word': config.wake_word,
                'enabled': config.enabled,
                'timeout_seconds': config.timeout_seconds
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config_data).encode())
            
        except Exception as e:
            logging.error(f"Wake word config get endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to get wake word configuration")
    
    def handle_wake_word_update_config(self):
        """Handle POST /voice/wake-word/config endpoint"""
        try:
            engine = self.get_wake_word_engine()
            if engine is None:
                self.send_error(503, "Wake word engine not available")
                return
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Request body is required")
                return
            
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON in request body")
                return
            
            # Extract configuration parameters
            wake_word = data.get('wake_word')
            enabled = data.get('enabled')
            
            # Validate at least one parameter is provided
            if wake_word is None and enabled is None:
                self.send_error(400, "At least one of 'wake_word' or 'enabled' must be provided")
                return
            
            # Update configuration
            try:
                engine.update_config(wake_word=wake_word, enabled=enabled)
            except ValueError as ve:
                self.send_error(400, f"Invalid configuration: {str(ve)}")
                return
            
            # TODO: Persist to /etc/turbopi/config.env for permanence across restarts
            # Currently runtime-only per initial implementation scope
            # Future enhancement: Update config file and reload on service restart
            
            # Return updated configuration
            config = engine.get_config()
            response_data = {
                'status': 'updated',
                'wake_word': config.wake_word,
                'enabled': config.enabled,
                'timeout_seconds': config.timeout_seconds
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
            logging.info(f"Wake word configuration updated: wake_word={config.wake_word}, enabled={config.enabled}")
            
        except Exception as e:
            logging.error(f"Wake word config update endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to update wake word configuration")
    
    def handle_stt(self):
        """Handle POST /voice/stt endpoint"""
        try:
            # Check if OpenAI API key is configured
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                logging.error("STT request failed: OPENAI_API_KEY not configured")
                self.send_error(500, "STT service not configured: Missing OPENAI_API_KEY")
                return
            
            # Validate Content-Type
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('audio/wav'):
                self.send_error(400, "Invalid Content-Type: Expected audio/wav")
                return
            
            # Read and validate Content-Length header
            content_length_header = self.headers.get('Content-Length')
            if content_length_header is None:
                content_length = 0
            else:
                try:
                    content_length = int(content_length_header)
                except (TypeError, ValueError):
                    self.send_error(400, "Invalid Content-Length header: must be an integer")
                    return
            
            if content_length < 0:
                self.send_error(400, "Invalid Content-Length header: must be non-negative")
                return
            
            if content_length == 0:
                self.send_error(400, "No audio data provided")
                return
            
            # Limit audio size to prevent memory issues (10MB max)
            max_size = 10 * 1024 * 1024  # 10MB
            if content_length > max_size:
                self.send_error(413, f"Audio file too large: Maximum size is {max_size} bytes")
                return
            
            audio_data = self.rfile.read(content_length)
            
            # Call OpenAI Whisper API
            try:
                # Prepare multipart/form-data request per RFC 2046
                boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
                boundary_bytes = boundary.encode('ascii')
                
                # Build multipart body with correct CRLF placement:
                # --boundary\r\n
                # Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n
                # Content-Type: audio/wav\r\n
                # \r\n
                # <audio_data>\r\n
                # --boundary\r\n
                # Content-Disposition: form-data; name="model"\r\n
                # \r\n
                # whisper-1\r\n
                # --boundary--\r\n
                body = (
                    b"--" + boundary_bytes + b"\r\n"
                    b'Content-Disposition: form-data; name="file"; filename="audio.wav"' + b"\r\n"
                    b"Content-Type: audio/wav" + b"\r\n"
                    b"\r\n"
                    + audio_data + b"\r\n"
                    + b"--" + boundary_bytes + b"\r\n"
                    + b'Content-Disposition: form-data; name="model"' + b"\r\n"
                    + b"\r\n"
                    + b"whisper-1" + b"\r\n"
                    + b"--" + boundary_bytes + b"--" + b"\r\n"
                )
                
                # Create request to OpenAI API
                openai_url = 'https://api.openai.com/v1/audio/transcriptions'
                req = urllib.request.Request(openai_url, data=body, method='POST')
                req.add_header('Authorization', f'Bearer {openai_api_key}')
                req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
                
                # Make API call
                with urllib.request.urlopen(req, timeout=30) as response:
                    response_data = json.loads(response.read().decode())
                    transcript = response_data.get('text', '')
                    
                    # Return transcript
                    result = {
                        'transcript': transcript
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                    
                    logging.info(f"STT completed successfully: {len(audio_data)} bytes -> {len(transcript)} chars")
                    
            except urllib.error.HTTPError as e:
                # Don't log error body as it may contain sensitive information
                logging.error(f"OpenAI API error: HTTP {e.code}")
                
                if e.code == 401:
                    self.send_error(500, "STT service authentication failed: Invalid API key")
                elif e.code == 429:
                    self.send_error(503, "STT service rate limit exceeded: Please try again later")
                else:
                    self.send_error(500, f"STT service error: OpenAI API returned {e.code}")
                    
            except urllib.error.URLError as e:
                logging.error(f"Network error calling OpenAI API: {e.reason}")
                self.send_error(503, "STT service unavailable: Network error")
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse OpenAI API response: {e}")
                self.send_error(500, "STT service error: Invalid response from OpenAI API")
                
        except Exception as e:
            logging.error(f"STT endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to process STT request")


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
