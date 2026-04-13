#!/usr/bin/env python3
"""
TurboPi Web UI Service (Skeleton)

This is a minimal skeleton implementation that provides:
- Simple web server for the UI
- Basic logging
- Configuration loading from environment variables
"""

import os
import sys
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler


# HTML template for the UI
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>{robot_name} Control Panel</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        h2 {{
            color: #444;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        .status {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .section {{
            margin: 20px 0;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 5px;
        }}
        .form-group {{
            margin: 15px 0;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        .form-group input[type="text"] {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }}
        .form-group input[type="checkbox"] {{
            width: 20px;
            height: 20px;
            margin-right: 10px;
            vertical-align: middle;
        }}
        .checkbox-label {{
            display: inline-block;
            vertical-align: middle;
            cursor: pointer;
        }}
        .button {{
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }}
        .button:hover {{
            background-color: #45a049;
        }}
        .button:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
        .alert {{
            padding: 12px;
            border-radius: 4px;
            margin: 15px 0;
            display: none;
        }}
        .alert.success {{
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .alert.error {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .info {{
            color: #666;
            font-size: 14px;
            margin-top: 10px;
        }}
        .current-value {{
            color: #2196F3;
            font-weight: bold;
        }}
        .button-secondary {{
            background-color: #2196F3;
        }}
        .button-secondary:hover {{
            background-color: #1976D2;
        }}
        .button-warning {{
            background-color: #FF9800;
        }}
        .button-warning:hover {{
            background-color: #F57C00;
        }}
        .button-danger {{
            background-color: #F44336;
        }}
        .button-danger:hover {{
            background-color: #D32F2F;
        }}
        .version-info p {{
            margin: 5px 0;
        }}
        .joystick-wrap {{
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .joystick-pad {{
            width: 220px;
            height: 220px;
            border-radius: 50%;
            border: 2px solid #bdbdbd;
            position: relative;
            background: radial-gradient(circle at center, #f5f5f5 0%, #ececec 70%, #e0e0e0 100%);
            touch-action: none;
        }}
        .joystick-knob {{
            width: 58px;
            height: 58px;
            border-radius: 50%;
            background: #607d8b;
            position: absolute;
            left: 81px;
            top: 81px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
        .control-stats p {{
            margin: 6px 0;
        }}
        .video-panel {{
            display: grid;
            gap: 10px;
        }}
        .video-frame {{
            width: 100%;
            max-width: 640px;
            border-radius: 8px;
            border: 1px solid #cfd8dc;
            background: #000;
            min-height: 240px;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{robot_name} Control Panel</h1>
        
        <div class="status">
            <h2>System Status</h2>
            <p>✓ API Service: Running on port {api_port}</p>
            <p>✓ UI Service: Running</p>
            <p>✓ Configuration: Loaded</p>
        </div>

        <div class="section">
            <h2>Voice Settings</h2>
            <div id="alert" class="alert"></div>
            
            <div class="form-group">
                <label>
                    <input type="checkbox" id="wakeWordEnabled">
                    <span class="checkbox-label">Enable Wake Word Detection</span>
                </label>
                <p class="info">When enabled, the robot listens for the wake word to activate voice commands.</p>
            </div>
            
            <div class="form-group">
                <label for="wakeWord">Wake Word:</label>
                <input type="text" id="wakeWord" placeholder="Enter wake word (e.g., Jarvis)">
                <p class="info">Current wake word: <span id="currentWakeWord" class="current-value">Loading...</span></p>
                <p class="info">The wake word must contain only ASCII characters and cannot be empty.</p>
            </div>
            
            <button class="button" onclick="saveWakeWordConfig()">Save Settings</button>
        </div>

        <div class="section">
            <h2>Software Updates</h2>
            <div id="update-alert" class="alert"></div>

            <div class="version-info">
                <p>Current version: <span id="currentVersion" class="current-value">Loading...</span></p>
                <p>Latest stable: <span id="latestVersion" class="current-value">Loading...</span></p>
            </div>

            <div style="margin-top:15px; display:flex; gap:10px; flex-wrap:wrap;">
                <button class="button button-secondary" id="checkUpdatesBtn" onclick="checkForUpdates()">Check for Updates</button>
                <button class="button" id="updateNowBtn" onclick="applyUpdate()" disabled>Update Now</button>
            </div>

            <hr style="margin:20px 0; border:none; border-top:1px solid #e0e0e0;">

            <h3 style="color:#444; margin-bottom:10px;">System Control</h3>
            <div id="system-alert" class="alert"></div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px;">
                <button class="button button-warning" onclick="restartServices()">Restart Services</button>
                <button class="button button-danger" onclick="rebootBot()">Reboot Bot</button>
            </div>
            <div class="info" style="background:#fff8e1; padding:12px; border-radius:4px; border-left:4px solid #ffc107;">
                <strong>Restart Services</strong> stops and restarts all TurboPi software services (API, UI, updater,
                voice) without rebooting the Raspberry Pi. Use this after a software update or when a service is
                unresponsive. Takes about 5–10 seconds; the page will briefly become unavailable.<br><br>
                <strong>Reboot Bot</strong> performs a full Linux reboot of the Raspberry Pi. All services stop,
                the OS shuts down cleanly, and the robot restarts from scratch. Use this for hardware-level
                troubleshooting or after OS-level changes. Takes about 30–60 seconds before the robot is
                accessible again.
            </div>
        </div>

        <div class="section">
            <h2>Teleoperation</h2>
            <div id="control-alert" class="alert"></div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px;">
                <button class="button" onclick="armMotors()">Arm</button>
                <button class="button button-warning" onclick="disarmMotors()">Disarm</button>
                <button class="button button-danger" onclick="engageEstop()">E-Stop</button>
                <button class="button button-secondary" onclick="resetEstop()">Reset E-Stop</button>
            </div>
            <div class="joystick-wrap">
                <div id="joystickPad" class="joystick-pad">
                    <div id="joystickKnob" class="joystick-knob"></div>
                </div>
                <div class="control-stats">
                    <p>WebSocket: <span id="wsStatus" class="current-value">connecting...</span></p>
                    <p>Armed: <span id="armedValue" class="current-value">no</span></p>
                    <p>E-Stop Latched: <span id="estopValue" class="current-value">no</span></p>
                    <p>Deadman Triggered: <span id="deadmanValue" class="current-value">no</span></p>
                    <p>Drive Linear: <span id="linearValue" class="current-value">0.00</span> m/s</p>
                    <p>Drive Angular: <span id="angularValue" class="current-value">0.00</span> rad/s</p>
                    <p class="info">Disconnect or missing heartbeat triggers immediate STOP.</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Vision</h2>
            <div class="video-panel">
                <img id="videoStream" class="video-frame" alt="Live camera stream" />
                <p>Stream: <span id="videoStatus" class="current-value">connecting...</span></p>
                <p>FPS: <span id="videoFps" class="current-value">0.0</span></p>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://' + window.location.hostname + ':{api_port}';
        const WS_BASE = 'ws://' + window.location.hostname + ':{ws_port}';
        const CONTROL_WS_PATH = '/ws/control';
        const VIDEO_STREAM_PATH = '/video/stream';
        const VIDEO_STATS_PATH = '/video/stats';
        let controlSocket = null;
        let heartbeatTimer = null;
        let dragActive = false;
        let controlMaxLinear = 0.5;
        let controlMaxAngular = 1.2;
        let videoReconnectTimer = null;

        // Load current wake word configuration on page load
        async function loadWakeWordConfig() {{
            try {{
                const response = await fetch(API_BASE + '/voice/wake-word/config');
                if (!response.ok) {{
                    throw new Error('Failed to load wake word configuration');
                }}
                const data = await response.json();
                
                document.getElementById('wakeWord').value = data.wake_word;
                document.getElementById('wakeWordEnabled').checked = data.enabled;
                document.getElementById('currentWakeWord').textContent = data.wake_word;
            }} catch (error) {{
                showAlert('Error loading wake word configuration: ' + error.message, 'error');
            }}
        }}
        
        // Save wake word configuration
        async function saveWakeWordConfig() {{
            const wakeWord = document.getElementById('wakeWord').value.trim();
            const enabled = document.getElementById('wakeWordEnabled').checked;
            
            // Validation
            if (!wakeWord) {{
                showAlert('Wake word cannot be empty', 'error');
                return;
            }}
            
            // Check for ASCII-only characters
            // Match only printable ASCII characters (space to tilde)
            if (!/^[ -~]+$/.test(wakeWord)) {{
                showAlert('Wake word must contain only ASCII characters', 'error');
                return;
            }}
            
            try {{
                const response = await fetch(API_BASE + '/voice/wake-word/config', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        wake_word: wakeWord,
                        enabled: enabled
                    }})
                }});
                
                if (!response.ok) {{
                    const errorText = await response.text();
                    throw new Error('Failed to save configuration: ' + errorText);
                }}
                
                const data = await response.json();
                document.getElementById('currentWakeWord').textContent = data.wake_word;
                showAlert('Wake word settings saved successfully!', 'success');
            }} catch (error) {{
                showAlert('Error saving configuration: ' + error.message, 'error');
            }}
        }}
        
        // Show alert message
        function showAlert(message, type) {{
            const alertDiv = document.getElementById('alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
            
            // Auto-hide success messages after 3 seconds
            if (type === 'success') {{
                setTimeout(() => {{
                    alertDiv.style.display = 'none';
                }}, 3000);
            }}
        }}

        function showUpdateAlert(message, type) {{
            const alertDiv = document.getElementById('update-alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
        }}

        function showSystemAlert(message, type) {{
            const alertDiv = document.getElementById('system-alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
            if (type === 'success') {{
                setTimeout(() => {{ alertDiv.style.display = 'none'; }}, 4000);
            }}
        }}

        function showControlAlert(message, type) {{
            const alertDiv = document.getElementById('control-alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
            if (type === 'success') {{
                setTimeout(() => {{ alertDiv.style.display = 'none'; }}, 2500);
            }}
        }}

        async function armMotors() {{
            const response = await fetch(API_BASE + '/control/arm', {{ method: 'POST' }});
            const payload = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(payload.message || 'Failed to arm', 'error');
                return;
            }}
            showControlAlert('Motors armed', 'success');
        }}

        async function disarmMotors() {{
            const response = await fetch(API_BASE + '/control/disarm', {{ method: 'POST' }});
            const payload = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(payload.message || 'Failed to disarm', 'error');
                return;
            }}
            stopJoystick();
            showControlAlert('Motors disarmed', 'success');
        }}

        async function engageEstop() {{
            const response = await fetch(API_BASE + '/control/estop', {{ method: 'POST' }});
            const payload = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(payload.message || 'Failed to engage E-Stop', 'error');
                return;
            }}
            stopJoystick();
            showControlAlert('E-Stop engaged', 'error');
            await refreshControlState();
        }}

        async function resetEstop() {{
            const response = await fetch(API_BASE + '/control/estop/reset', {{ method: 'POST' }});
            const payload = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(payload.message || 'Failed to reset E-Stop', 'error');
                return;
            }}
            showControlAlert('E-Stop reset. Arm to drive again.', 'success');
            await refreshControlState();
        }}

        function connectControlSocket() {{
            controlSocket = new WebSocket(WS_BASE + CONTROL_WS_PATH);
            controlSocket.onopen = () => {{
                document.getElementById('wsStatus').textContent = 'connected';
                heartbeatTimer = setInterval(() => {{
                    if (controlSocket && controlSocket.readyState === WebSocket.OPEN) {{
                        controlSocket.send(JSON.stringify({{ type: 'heartbeat' }}));
                    }}
                }}, 200);
            }};
            controlSocket.onclose = () => {{
                document.getElementById('wsStatus').textContent = 'disconnected';
                if (heartbeatTimer) clearInterval(heartbeatTimer);
                setTimeout(connectControlSocket, 1000);
            }};
        }}

        function sendDrive(linear, angular) {{
            document.getElementById('linearValue').textContent = linear.toFixed(2);
            document.getElementById('angularValue').textContent = angular.toFixed(2);
            if (!controlSocket || controlSocket.readyState !== WebSocket.OPEN) return;
            controlSocket.send(JSON.stringify({{
                type: 'drive',
                linear: linear,
                angular: angular
            }}));
        }}

        function stopJoystick() {{
            document.getElementById('joystickKnob').style.left = '81px';
            document.getElementById('joystickKnob').style.top = '81px';
            if (controlSocket && controlSocket.readyState === WebSocket.OPEN) {{
                controlSocket.send(JSON.stringify({{ type: 'stop' }}));
            }}
            document.getElementById('linearValue').textContent = '0.00';
            document.getElementById('angularValue').textContent = '0.00';
        }}

        function setupJoystick() {{
            const pad = document.getElementById('joystickPad');
            const knob = document.getElementById('joystickKnob');
            const radius = 81;

            function updateFromEvent(event) {{
                const rect = pad.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                let dx = event.clientX - centerX;
                let dy = event.clientY - centerY;
                const distance = Math.sqrt(dx * dx + dy * dy);
                if (distance > radius) {{
                    dx = (dx / distance) * radius;
                    dy = (dy / distance) * radius;
                }}

                knob.style.left = (81 + dx) + 'px';
                knob.style.top = (81 + dy) + 'px';

                const linear = (-dy / radius) * controlMaxLinear;
                const angular = (dx / radius) * controlMaxAngular;
                sendDrive(linear, angular);
            }}

            pad.addEventListener('pointerdown', (event) => {{
                dragActive = true;
                pad.setPointerCapture(event.pointerId);
                updateFromEvent(event);
            }});

            pad.addEventListener('pointermove', (event) => {{
                if (!dragActive) return;
                updateFromEvent(event);
            }});

            function release() {{
                dragActive = false;
                stopJoystick();
            }}

            pad.addEventListener('pointerup', release);
            pad.addEventListener('pointercancel', release);
            pad.addEventListener('pointerleave', () => {{ if (dragActive) release(); }});
        }}

        async function refreshControlState() {{
            try {{
                const response = await fetch(API_BASE + '/control/state');
                if (!response.ok) return;
                const data = await response.json();
                document.getElementById('armedValue').textContent = data.armed ? 'yes' : 'no';
                document.getElementById('estopValue').textContent = data.estop_latched ? 'yes' : 'no';
                document.getElementById('deadmanValue').textContent = data.deadman_triggered ? 'yes' : 'no';
                if (typeof data.max_linear_speed === 'number') {{
                    controlMaxLinear = data.max_linear_speed;
                }}
                if (typeof data.max_angular_speed === 'number') {{
                    controlMaxAngular = data.max_angular_speed;
                }}
            }} catch (error) {{
                // Keep UI responsive when API is restarting.
            }}
        }}

        function startVideoStream() {{
            const img = document.getElementById('videoStream');
            const statusEl = document.getElementById('videoStatus');
            const streamUrl = API_BASE + VIDEO_STREAM_PATH + '?seconds=20&t=' + Date.now();
            statusEl.textContent = 'connecting...';
            img.src = streamUrl;
        }}

        function setupVideoPanel() {{
            const img = document.getElementById('videoStream');
            const statusEl = document.getElementById('videoStatus');
            const fpsEl = document.getElementById('videoFps');

            img.onerror = () => {{
                statusEl.textContent = 'reconnecting...';
                if (videoReconnectTimer) {{
                    clearTimeout(videoReconnectTimer);
                }}
                videoReconnectTimer = setTimeout(startVideoStream, 1000);
            }};

            setInterval(async () => {{
                try {{
                    const response = await fetch(API_BASE + VIDEO_STATS_PATH);
                    if (!response.ok) return;
                    const stats = await response.json();
                    fpsEl.textContent = (stats.fps || 0).toFixed(1);
                    statusEl.textContent = stats.active ? 'live' : 'idle';
                }} catch (error) {{
                    statusEl.textContent = 'reconnecting...';
                }}
            }}, 1000);

            startVideoStream();
        }}

        async function parseApiPayload(response) {{
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {{
                return await response.json();
            }}

            const text = await response.text();
            return text ? {{ message: text }} : {{}};
        }}

        async function getApiErrorMessage(response, fallbackMessage) {{
            const payload = await parseApiPayload(response);
            return payload.message || payload.error || fallbackMessage;
        }}

        async function loadVersionInfo() {{
            try {{
                const response = await fetch(API_BASE + '/system/version');
                if (!response.ok) throw new Error('Failed to load version info');
                const data = await response.json();
                document.getElementById('currentVersion').textContent = data.current || 'unknown';
                document.getElementById('latestVersion').textContent = data.latest_stable || 'unknown';
            }} catch (error) {{
                document.getElementById('currentVersion').textContent = 'unavailable';
                document.getElementById('latestVersion').textContent = 'unavailable';
            }}
        }}

        async function checkForUpdates() {{
            const btn = document.getElementById('checkUpdatesBtn');
            btn.disabled = true;
            btn.textContent = 'Checking...';
            showUpdateAlert('', '');
            document.getElementById('update-alert').style.display = 'none';
            try {{
                const response = await fetch(API_BASE + '/updates/check');
                if (!response.ok) throw new Error('Check failed: ' + response.status);
                const data = await response.json();
                await loadVersionInfo();
                if (data.update_available) {{
                    showUpdateAlert(
                        'Update available: ' + (data.latest_version || 'new version') +
                        '. Click "Update Now" to install.',
                        'success'
                    );
                    document.getElementById('updateNowBtn').disabled = false;
                }} else {{
                    showUpdateAlert('You are running the latest stable version.', 'success');
                    document.getElementById('updateNowBtn').disabled = true;
                }}
            }} catch (error) {{
                showUpdateAlert('Error checking for updates: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Check for Updates';
            }}
        }}

        async function applyUpdate() {{
            if (!confirm('Apply the update now? The robot services will restart automatically. Confirm?')) return;
            const btn = document.getElementById('updateNowBtn');
            btn.disabled = true;
            showUpdateAlert('Update started. Services will restart shortly — this page may be temporarily unavailable.', 'success');
            try {{
                const response = await fetch(API_BASE + '/updates/apply', {{ method: 'POST' }});
                const data = await parseApiPayload(response);

                if (!response.ok) {{
                    throw new Error(data.message || data.error || 'Update failed');
                }}

                if (response.status === 200) {{
                    showUpdateAlert(data.message || 'Already on latest version.', 'success');
                }} else if (response.status === 202) {{
                    showUpdateAlert(
                        (data.message || 'Update initiated.') +
                        ' Reload this page in 30–60 seconds.',
                        'success'
                    );
                }} else {{
                    throw new Error(data.message || 'Update failed');
                }}
            }} catch (error) {{
                showUpdateAlert('Error applying update: ' + error.message, 'error');
                btn.disabled = false;
            }}
        }}

        async function restartServices() {{
            if (!confirm('Restart all TurboPi services? The page will be briefly unavailable.')) return;
            showSystemAlert('Restarting services…', 'success');
            try {{
                const response = await fetch(API_BASE + '/system/restart', {{ method: 'POST' }});
                if (!response.ok) {{
                    throw new Error(await getApiErrorMessage(response, 'Restart request failed.'));
                }}
            }} catch (error) {{
                if (error instanceof TypeError) {{
                    showSystemAlert('Services are restarting. Reload this page in 10–15 seconds.', 'success');
                    return;
                }}
                showSystemAlert('Error restarting services: ' + error.message, 'error');
                return;
            }}
            showSystemAlert('Services are restarting. Reload this page in 10–15 seconds.', 'success');
        }}

        async function rebootBot() {{
            if (!confirm('Reboot the robot? It will be offline for about 30–60 seconds.')) return;
            showSystemAlert('Rebooting…', 'success');
            try {{
                const response = await fetch(API_BASE + '/system/reboot', {{ method: 'POST' }});
                if (!response.ok) {{
                    throw new Error(await getApiErrorMessage(response, 'Reboot request failed.'));
                }}
            }} catch (error) {{
                if (error instanceof TypeError) {{
                    showSystemAlert('Robot is rebooting. Reload this page in 30–60 seconds.', 'success');
                    return;
                }}
                showSystemAlert('Error rebooting robot: ' + error.message, 'error');
                return;
            }}
            showSystemAlert('Robot is rebooting. Reload this page in 30–60 seconds.', 'success');
        }}
        
        // Load configuration when page loads
        window.addEventListener('DOMContentLoaded', () => {{
            loadWakeWordConfig();
            loadVersionInfo();
            connectControlSocket();
            setupJoystick();
            setupVideoPanel();
            refreshControlState();
            setInterval(refreshControlState, 500);
        }});
    </script>
</body>
</html>"""


class UIHandler(SimpleHTTPRequestHandler):
    """Minimal HTTP handler for the UI service"""

    def log_message(self, format, *args):
        """Override to log to stdout instead of stderr"""
        sys.stdout.write("%s - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')
            api_port = os.environ.get('API_PORT', '8080')
            ws_port = os.environ.get('API_WS_PORT', '8765')
            
            html = HTML_TEMPLATE.format(robot_name=robot_name, api_port=api_port, ws_port=ws_port)
            self.wfile.write(html.encode())
        else:
            self.send_error(404, "Not Found")


def main():
    """Main entry point for the UI service"""
    # Configure logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Load configuration from environment
    host = os.environ.get('UI_HOST', '0.0.0.0')
    
    # Validate and parse port
    try:
        port = int(os.environ.get('UI_PORT', '8081'))
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
    except ValueError as e:
        logging.error(f"Invalid UI_PORT configuration: {e}")
        sys.exit(1)
    
    robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')

    logging.info(f"TurboPi Web UI starting...")
    logging.info(f"Robot Name: {robot_name}")
    logging.info(f"Listening on {host}:{port}")
    logging.info(f"Access UI at: http://{host}:{port}/")

    # Create and start HTTP server
    server = HTTPServer((host, port), UIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("\nShutting down UI service...")
        server.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
