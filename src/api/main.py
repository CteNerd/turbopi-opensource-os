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
import subprocess
import time
import urllib.request
import urllib.error
import urllib.parse
import threading
import re
import asyncio
import base64
import io
import tarfile
import tempfile
from typing import Optional, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

try:
    from websockets.legacy.server import serve as ws_serve
    WS_IMPORT_ERROR = None
except Exception as exc:
    ws_serve = None
    WS_IMPORT_ERROR = exc

# Add control/HAL imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from control import ControlArbiter, ControlWebSocketBridge
from hal import CameraError, FakeCameraHAL

# Import wake word engine and command parser (add path for imports)
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

try:
    from command_intent import CommandIntentParser
    COMMAND_PARSER_AVAILABLE = True
except ImportError:
    COMMAND_PARSER_AVAILABLE = False
    logging.warning("Command intent parser not available")


SYSTEM_ACTION_DELAY_SECONDS = 0.5
MJPEG_BOUNDARY = 'frame'
DEFAULT_VIDEO_STREAM_SECONDS = 15.0
SERVICE_STATE_CACHE_TTL_SECONDS = 2.0
FALLBACK_JPEG_BYTES = base64.b64decode(
    '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAAQABADASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAVEAEBAAAAAAAAAAAAAAAAAAAAAf/aAAwDAQACEAMQAAAByA//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAEFAqf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/AYf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/AYf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAY/Aqf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/Idf/2gAMAwEAAgADAAAAED//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EH//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EH//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EH//2Q=='
)

_SERVICE_STATE_CACHE = {'timestamp': 0.0, 'states': {}}
_SERVICE_STATE_CACHE_LOCK = threading.Lock()


def is_valid_control_ws_origin(origin: Optional[str], host_header: Optional[str], ui_port: int) -> bool:
    """Validate websocket control connections come from same-host UI origin."""
    if not origin or not host_header:
        return False

    parsed_origin = urllib.parse.urlparse(origin)
    if parsed_origin.scheme not in ('http', 'https') or not parsed_origin.hostname:
        return False

    request_host = host_header.split(':', 1)[0].lower()
    if parsed_origin.hostname.lower() != request_host:
        return False

    return parsed_origin.port == ui_port


def get_current_version() -> str:
    """
    Get the current version from environment variable.
    
    Returns:
        Current version string from VERSION env var, defaults to '0.1.0-dev'
    """
    return os.environ.get('VERSION', '0.1.0-dev')


def redact_secrets(text: str) -> str:
    """Redact common secret patterns from logs/config text."""
    patterns = [
        (r'(OPENAI_API_KEY\s*=\s*)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(password\s*[=:]\s*)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(wpa_passphrase\s*=\s*)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(Authorization:\s*Bearer\s+)([^\s\n]+)', r'\1***REDACTED***'),
        (r'(api[_-]?key\s*[=:]\s*)([^\s\n]+)', r'\1***REDACTED***'),
        (r'("(?:password|token|api_key)"\s*:\s*")([^"]+)(")', r'\1***REDACTED***\3'),
    ]
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted


def _safe_run(command, timeout: int = 3) -> str:
    """Run system commands safely and return output text."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return (result.stdout or '').strip()
    except Exception:
        return ''


def _service_state(service_name: str) -> str:
    """Return systemd service state string for diagnostics."""
    value = _safe_run(['systemctl', 'is-active', service_name], timeout=2)
    return value or 'unknown'


def _cached_service_states() -> Dict[str, str]:
    """Cache service state lookups briefly to avoid repeated shelling per /health poll."""
    now = time.monotonic()
    with _SERVICE_STATE_CACHE_LOCK:
        age = now - _SERVICE_STATE_CACHE['timestamp']
        if age <= SERVICE_STATE_CACHE_TTL_SECONDS and _SERVICE_STATE_CACHE['states']:
            return dict(_SERVICE_STATE_CACHE['states'])

        states = {
            'api': _service_state('turbopi-api'),
            'ui': _service_state('turbopi-ui'),
            'updater': _service_state('turbopi-updater'),
            'wake_word': _service_state('turbopi-wake-word'),
        }
        _SERVICE_STATE_CACHE['timestamp'] = now
        _SERVICE_STATE_CACHE['states'] = states
        return dict(states)


def persist_wake_word_config(wake_word: Optional[str], enabled: Optional[bool]) -> bool:
    """Persist wake-word settings to config.env while preserving unrelated keys."""
    config_path = os.environ.get('CONFIG_ENV_PATH', '/etc/turbopi/config.env')
    existing_lines = []
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as handle:
                existing_lines = handle.readlines()
        except Exception:
            return False

    replacements = {}
    if wake_word is not None:
        replacements['WAKE_WORD'] = wake_word
    if enabled is not None:
        replacements['WAKE_WORD_ENABLED'] = 'true' if enabled else 'false'

    if not replacements:
        return True

    seen = set()
    updated_lines = []
    for line in existing_lines:
        if '=' not in line or line.lstrip().startswith('#'):
            updated_lines.append(line)
            continue

        key, _sep, _value = line.partition('=')
        clean_key = key.strip()
        if clean_key in replacements:
            updated_lines.append(f'{clean_key}={replacements[clean_key]}\n')
            seen.add(clean_key)
        else:
            updated_lines.append(line)

    for key, value in replacements.items():
        if key not in seen:
            updated_lines.append(f'{key}={value}\n')

    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        tmp_path = f'{config_path}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as handle:
            handle.writelines(updated_lines)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, config_path)
        return True
    except Exception:
        return False


def _disk_usage(path: str = '/') -> Dict[str, float]:
    """Return disk usage stats in MB for the provided mount path."""
    try:
        stat = os.statvfs(path)
        total = (stat.f_blocks * stat.f_frsize) / (1024 * 1024)
        free = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        used = total - free
        return {
            'total_mb': round(total, 1),
            'used_mb': round(used, 1),
            'free_mb': round(free, 1),
        }
    except Exception:
        return {'total_mb': 0.0, 'used_mb': 0.0, 'free_mb': 0.0}


def _memory_usage() -> Dict[str, float]:
    """Return memory stats in MB parsed from /proc/meminfo when available."""
    try:
        with open('/proc/meminfo', 'r', encoding='utf-8') as handle:
            content = handle.read()
        total_match = re.search(r'^MemTotal:\s+(\d+)\s+kB$', content, flags=re.MULTILINE)
        avail_match = re.search(r'^MemAvailable:\s+(\d+)\s+kB$', content, flags=re.MULTILINE)
        if not total_match or not avail_match:
            return {'total_mb': 0.0, 'used_mb': 0.0, 'available_mb': 0.0}
        total = int(total_match.group(1)) / 1024.0
        available = int(avail_match.group(1)) / 1024.0
        used = total - available
        return {
            'total_mb': round(total, 1),
            'used_mb': round(used, 1),
            'available_mb': round(available, 1),
        }
    except Exception:
        return {'total_mb': 0.0, 'used_mb': 0.0, 'available_mb': 0.0}


def build_health_snapshot() -> Dict[str, object]:
    """Build expanded health payload for API and diagnostics bundle."""
    uptime_seconds = 0.0
    try:
        with open('/proc/uptime', 'r', encoding='utf-8') as handle:
            uptime_seconds = float(handle.readline().split()[0])
    except Exception:
        uptime_seconds = 0.0

    cpu_temp = None
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r', encoding='utf-8') as handle:
            cpu_temp = float(handle.read().strip()) / 1000.0
    except Exception:
        cpu_temp = None

    return {
        'status': 'ok',
        'uptime': uptime_seconds,
        'cpu_temp': cpu_temp,
        'version': get_current_version(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'memory': _memory_usage(),
        'disk': _disk_usage('/'),
        'services': _cached_service_states(),
    }


def build_diagnostics_bundle() -> bytes:
    """Create gzipped tar diagnostics bundle with redacted logs/config."""
    health_snapshot = build_health_snapshot()
    config_path = os.environ.get('DIAGNOSTICS_CONFIG_PATH', '/etc/turbopi/config.env')
    config_raw = ''
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as handle:
                config_raw = handle.read()
        except Exception:
            config_raw = ''

    journal_output = _safe_run(
        ['journalctl', '--no-pager', '-n', '300', '-u', 'turbopi-api', '-u', 'turbopi-ui', '-u', 'turbopi-updater'],
        timeout=5,
    )

    files = {
        'health.json': json.dumps(health_snapshot, indent=2),
        'config.env.redacted': redact_secrets(config_raw),
        'logs/systemd.log.redacted': redact_secrets(journal_output),
        'meta.txt': 'TurboPi diagnostics bundle\nContains redacted support data.\n',
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        for name, content in files.items():
            abs_path = os.path.join(tmp_dir, name)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as handle:
                handle.write(content)

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as tar_handle:
            for name in files:
                tar_handle.add(os.path.join(tmp_dir, name), arcname=name)
        return buffer.getvalue()


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
    
    # Global command parser instance (shared across requests)
    _command_parser: Optional['CommandIntentParser'] = None
    _command_parser_lock = threading.Lock()

    # Global control arbiter for teleoperation
    _control_arbiter: Optional[ControlArbiter] = None
    _control_lock = threading.Lock()

    # Global camera HAL for video streaming
    _camera_hal: Optional[FakeCameraHAL] = None
    _camera_lock = threading.Lock()
    _video_stats_lock = threading.Lock()
    _video_frames_total = 0
    _video_last_frame_ts = 0.0
    _video_fps = 0.0
    
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
    
    @classmethod
    def get_command_parser(cls):
        """Get or create command parser instance (singleton pattern)"""
        if not COMMAND_PARSER_AVAILABLE:
            return None
        
        with cls._command_parser_lock:
            if cls._command_parser is None:
                cls._command_parser = CommandIntentParser()
                logging.info("Command intent parser initialized")
            return cls._command_parser

    @classmethod
    def get_control_arbiter(cls):
        """Get or create control arbiter singleton."""
        with cls._control_lock:
            if cls._control_arbiter is None:
                cls._control_arbiter = ControlArbiter()
                logging.info("Control arbiter initialized")
            return cls._control_arbiter

    @classmethod
    def get_camera_hal(cls):
        """Get or create camera HAL singleton used by MJPEG stream endpoint."""
        with cls._camera_lock:
            if cls._camera_hal is None:
                cls._camera_hal = FakeCameraHAL()
                cls._camera_hal.open()
                logging.info("Camera HAL initialized for video stream")
            elif not cls._camera_hal.is_open():
                cls._camera_hal.open()
            return cls._camera_hal

    @classmethod
    def record_video_frame(cls) -> None:
        """Record frame timing metrics for UI diagnostics."""
        now = time.monotonic()
        with cls._video_stats_lock:
            if cls._video_last_frame_ts > 0:
                delta = now - cls._video_last_frame_ts
                if delta > 0:
                    cls._video_fps = 1.0 / delta
            cls._video_last_frame_ts = now
            cls._video_frames_total += 1

    @classmethod
    def get_video_stats(cls) -> Dict[str, object]:
        """Return current video stream stats for UI FPS display."""
        now = time.monotonic()
        with cls._video_stats_lock:
            active = cls._video_last_frame_ts > 0 and (now - cls._video_last_frame_ts) < 2.0
            return {
                'fps': round(cls._video_fps, 1),
                'frames_total': cls._video_frames_total,
                'active': active,
            }

    def log_message(self, format, *args):
        """Override to log to stdout instead of stderr"""
        sys.stdout.write("%s - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))

    def _send_json_response(self, status_code: int, payload: Dict):
        """Send a JSON response with the provided status code."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _get_allowed_ui_origin(self) -> Optional[str]:
        """Return the allowed UI origin for this request when present."""
        origin = self.headers.get('Origin')
        if not origin:
            return None

        parsed_origin = urllib.parse.urlparse(origin)
        if parsed_origin.scheme not in ('http', 'https') or not parsed_origin.hostname:
            return None

        request_host = (self.headers.get('Host') or '').split(':', 1)[0].lower()
        if not request_host:
            return None

        ui_port = int(os.environ.get('UI_PORT', '8081'))
        if parsed_origin.port != ui_port:
            return None

        if parsed_origin.hostname.lower() != request_host:
            return None

        return f"{parsed_origin.scheme}://{parsed_origin.netloc}"

    def _require_ui_origin(self) -> bool:
        """Require a same-host UI origin for dangerous system actions."""
        header_value = self.headers.get('Origin') or self.headers.get('Referer')
        if not header_value:
            self._send_json_response(403, {
                'error': 'forbidden',
                'message': 'Requests to this endpoint must originate from the TurboPi UI.'
            })
            return False

        parsed_header = urllib.parse.urlparse(header_value)
        if parsed_header.scheme not in ('http', 'https') or not parsed_header.hostname:
            self._send_json_response(403, {
                'error': 'forbidden',
                'message': 'Requests to this endpoint must originate from the TurboPi UI.'
            })
            return False

        request_host = (self.headers.get('Host') or '').split(':', 1)[0].lower()
        ui_port = int(os.environ.get('UI_PORT', '8081'))
        if parsed_header.hostname.lower() != request_host or parsed_header.port != ui_port:
            self._send_json_response(403, {
                'error': 'forbidden',
                'message': 'Requests to this endpoint must originate from the TurboPi UI.'
            })
            return False

        return True

    def _run_delayed_command(self, command, timeout: int):
        """Run a system command after the response has been flushed to the client."""
        time.sleep(SYSTEM_ACTION_DELAY_SECONDS)
        try:
            subprocess.run(command, check=False, timeout=timeout)
        except Exception as exc:
            logging.error("Command execution error for %s: %s", command[0], exc)

    def end_headers(self):
        """Add CORS headers to all responses"""
        allowed_origin = self._get_allowed_ui_origin()
        if allowed_origin:
            self.send_header('Access-Control-Allow-Origin', allowed_origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/health':
            self.handle_health()
        elif path == '/control/state':
            self.handle_control_state()
        elif path == '/system/version':
            self.handle_system_version()
        elif path == '/updates/check':
            self.handle_updates_check()
        elif path == '/video/stream':
            self.handle_video_stream(parsed.query)
        elif path == '/video/stats':
            self.handle_video_stats()
        elif path == '/diagnostics/bundle':
            self.handle_diagnostics_bundle()
        elif path == '/voice/wake-word/status':
            self.handle_wake_word_status()
        elif path == '/voice/wake-word/config':
            self.handle_wake_word_get_config()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/updates/apply':
            self.handle_updates_apply()
        elif self.path == '/control/arm':
            self.handle_control_arm()
        elif self.path == '/control/disarm':
            self.handle_control_disarm()
        elif self.path == '/control/estop':
            self.handle_control_estop()
        elif self.path == '/control/estop/reset':
            self.handle_control_estop_reset()
        elif self.path == '/system/restart':
            self.handle_system_restart()
        elif self.path == '/system/reboot':
            self.handle_system_reboot()
        elif self.path == '/voice/wake-word/config':
            self.handle_wake_word_update_config()
        elif self.path == '/voice/stt':
            self.handle_stt()
        elif self.path == '/voice/command':
            self.handle_voice_command()
        else:
            self.send_error(404, "Not Found")

    def handle_health(self):
        """Handle /health endpoint"""
        try:
            health_data = build_health_snapshot()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode())
        except Exception as e:
            # Log the detailed error internally
            logging.error(f"Health endpoint error: {str(e)}")
            # Return generic error message to client
            self.send_error(500, "Internal Server Error: Unable to retrieve health status")

    def handle_diagnostics_bundle(self):
        """Handle GET /diagnostics/bundle endpoint."""
        try:
            if not self._require_ui_origin():
                return
            payload = build_diagnostics_bundle()
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            filename = f'turbopi-diagnostics-{timestamp}.tar.gz'
            self.send_response(200)
            self.send_header('Content-Type', 'application/gzip')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            logging.error('Failed to build diagnostics bundle: %s', exc)
            self.send_error(500, 'Internal Server Error: Unable to generate diagnostics bundle')

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

    def handle_system_restart(self):
        """Handle POST /system/restart — restart all TurboPi systemd services."""
        if not self._require_ui_origin():
            return

        self.send_response(202)
        self.end_headers()
        logging.info("Service restart requested via API")

        t = threading.Thread(
            target=self._run_delayed_command,
            args=(
                ['systemctl', 'try-restart',
                 'turbopi-api', 'turbopi-ui', 'turbopi-updater',
                 'turbopi-wake-word'],
                30,
            ),
            daemon=True,
        )
        t.start()

    def handle_system_reboot(self):
        """Handle POST /system/reboot — reboot the Raspberry Pi."""
        if not self._require_ui_origin():
            return

        self.send_response(202)
        self.end_headers()
        logging.info("System reboot requested via API")

        t = threading.Thread(
            target=self._run_delayed_command,
            args=(['reboot'], 10),
            daemon=True,
        )
        t.start()

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

    def handle_control_arm(self):
        """Handle POST /control/arm endpoint."""
        if not self._require_ui_origin():
            return
        arbiter = self.get_control_arbiter()
        result = arbiter.arm()
        status_code = 200 if result.get('status') == 'armed' else 409
        self._send_json_response(status_code, result)

    def handle_control_disarm(self):
        """Handle POST /control/disarm endpoint."""
        if not self._require_ui_origin():
            return
        arbiter = self.get_control_arbiter()
        self._send_json_response(200, arbiter.disarm())

    def handle_control_estop(self):
        """Handle POST /control/estop endpoint."""
        if not self._require_ui_origin():
            return
        arbiter = self.get_control_arbiter()
        self._send_json_response(200, arbiter.engage_estop())

    def handle_control_estop_reset(self):
        """Handle POST /control/estop/reset endpoint."""
        if not self._require_ui_origin():
            return
        arbiter = self.get_control_arbiter()
        self._send_json_response(200, arbiter.clear_estop())

    def handle_control_state(self):
        """Handle GET /control/state endpoint."""
        arbiter = self.get_control_arbiter()
        self._send_json_response(200, arbiter.get_state().to_dict())

    def handle_video_stream(self, query: str):
        """Handle GET /video/stream endpoint with multipart MJPEG output."""
        camera = self.get_camera_hal()
        max_frames = 0
        max_seconds = DEFAULT_VIDEO_STREAM_SECONDS
        query_params = urllib.parse.parse_qs(query)
        if 'frames' in query_params:
            try:
                max_frames = max(int(query_params['frames'][0]), 0)
            except (ValueError, TypeError):
                max_frames = 0
        if 'seconds' in query_params:
            try:
                max_seconds = max(float(query_params['seconds'][0]), 0.1)
            except (ValueError, TypeError):
                max_seconds = DEFAULT_VIDEO_STREAM_SECONDS

        try:
            calibration = camera.calibration
            frame_interval_s = 1.0 / max(calibration.fps, 1)
            stream_started_at = time.monotonic()

            self.send_response(200)
            self.send_header('Content-Type', f'multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()

            sent_frames = 0
            while True:
                try:
                    frame = camera.get_frame()
                except CameraError:
                    # Re-open once if the camera was closed by a service restart race.
                    camera.open()
                    frame = camera.get_frame()

                # Use native JPEG payload when available; otherwise emit deterministic fallback JPEG.
                frame_data = frame.data
                if frame_data.startswith(b'\xff\xd8') and frame_data.endswith(b'\xff\xd9'):
                    jpeg_data = frame_data
                else:
                    jpeg_data = FALLBACK_JPEG_BYTES
                payload = (
                    f'--{MJPEG_BOUNDARY}\r\n'
                    'Content-Type: image/jpeg\r\n'
                    f'Content-Length: {len(jpeg_data)}\r\n\r\n'
                ).encode('ascii') + jpeg_data + b'\r\n'

                self.wfile.write(payload)
                self.wfile.flush()
                self.record_video_frame()
                sent_frames += 1
                if max_frames and sent_frames >= max_frames:
                    break
                if (time.monotonic() - stream_started_at) >= max_seconds:
                    break
                time.sleep(frame_interval_s)
        except (BrokenPipeError, ConnectionResetError):
            logging.info('Video stream client disconnected')
        except Exception as exc:
            logging.error('Video stream error: %s', exc)

    def handle_video_stats(self):
        """Handle GET /video/stats endpoint."""
        self._send_json_response(200, self.get_video_stats())
    
    def handle_updates_apply(self):
        """Handle /updates/apply endpoint"""
        try:
            if not self._require_ui_origin():
                return

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
            persisted = persist_wake_word_config(config.wake_word, config.enabled)
            if not persisted:
                logging.warning('Wake word configuration updated in runtime but failed to persist to config.env')

            response_data = {
                'status': 'updated',
                'wake_word': config.wake_word,
                'enabled': config.enabled,
                'timeout_seconds': config.timeout_seconds,
                'persisted': persisted,
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
    
    def handle_voice_command(self):
        """
        Handle POST /voice/command endpoint
        
        Parses a voice transcript into a command intent that will be routed
        through the safety arbiter. This endpoint does NOT execute commands.
        """
        try:
            parser = self.get_command_parser()
            if parser is None:
                self.send_error(503, "Command parser not available")
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
            
            # Extract transcript
            transcript = data.get('transcript')
            if not transcript:
                self.send_error(400, "Missing required field: transcript")
                return
            
            # Parse command intent
            intent = parser.parse(transcript)
            
            # Log the parsed intent for audit trail
            logging.info(
                f"Voice command parsed: command={intent.command.value}, "
                f"target={intent.target}, valid={intent.is_valid()}, "
                f"confidence={intent.confidence}"
            )
            
            # Return intent (does NOT execute - routing to arbiter is external)
            result = intent.to_dict()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            logging.error(f"Voice command endpoint error: {str(e)}")
            self.send_error(500, "Internal Server Error: Unable to parse voice command")


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

    try:
        ws_port = int(os.environ.get('API_WS_PORT', '8765'))
        if not (1 <= ws_port <= 65535):
            raise ValueError(f"WebSocket port must be between 1 and 65535, got {ws_port}")
    except ValueError as e:
        logging.error(f"Invalid API_WS_PORT configuration: {e}")
        sys.exit(1)

    if ws_serve is None:
        logging.error('websockets package is required for /ws/control channel: %s', WS_IMPORT_ERROR)
        sys.exit(1)
    
    robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')

    logging.info(f"TurboPi API Backend starting...")
    logging.info(f"Robot Name: {robot_name}")
    logging.info(f"Listening on {host}:{port}")
    logging.info(f"Health endpoint: http://{host}:{port}/health")

    # Start websocket control channel in a background thread.
    arbiter = APIHandler.get_control_arbiter()
    bridge = ControlWebSocketBridge(arbiter)
    ui_port = int(os.environ.get('UI_PORT', '8081'))

    def run_websocket_server():
        async def ws_handler(websocket, path):
            if path != '/ws/control':
                await websocket.close(code=1008, reason='Invalid path')
                return

            origin = websocket.request_headers.get('Origin')
            host_header = websocket.request_headers.get('Host')
            if not is_valid_control_ws_origin(origin, host_header, ui_port):
                await websocket.close(code=1008, reason='Forbidden origin')
                return

            connection_id = id(websocket)
            bridge.connect(connection_id)
            try:
                async for message in websocket:
                    result = bridge.handle_text(connection_id, message)
                    await websocket.send(json.dumps(result))
            finally:
                bridge.disconnect(connection_id)

        async def runner():
            async with ws_serve(ws_handler, host, ws_port):
                logging.info(f"Control WebSocket listening on ws://{host}:{ws_port}/ws/control")
                while True:
                    APIHandler.get_control_arbiter().check_safety()
                    await asyncio.sleep(0.05)

        asyncio.run(runner())

    threading.Thread(target=run_websocket_server, daemon=True).start()

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
