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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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

        .mobile-tabs {{
            display: none;
        }}
        @media (max-width: 768px) {{
            body {{
                margin: 0;
                padding: 0;
            }}
            .container {{
                padding: 12px;
                box-shadow: none;
                border-radius: 0;
            }}
            h1 {{
                font-size: 1.3rem;
                margin-top: 12px;
                margin-bottom: 4px;
            }}
            .status {{
                display: none;
            }}
            .mobile-tabs {{
                display: flex;
                position: sticky;
                top: 0;
                z-index: 100;
                background: #fff;
                border-bottom: 2px solid #e0e0e0;
                margin: 8px -12px 16px;
                padding: 0;
            }}
            .tab-btn {{
                flex: 1;
                padding: 12px 8px;
                border: none;
                border-bottom: 3px solid transparent;
                background: transparent;
                font-size: 15px;
                font-weight: 600;
                color: #888;
                cursor: pointer;
            }}
            .tab-btn.active {{
                color: #4CAF50;
                border-bottom-color: #4CAF50;
            }}
            .section[data-tab] {{
                display: none;
            }}
            .section[data-tab].tab-visible {{
                display: block;
            }}
            .control-btn-grid {{
                display: grid !important;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}
            .control-btn-grid .button {{
                margin-top: 0;
                width: 100%;
                padding: 14px 10px;
                font-size: 15px;
            }}
            .joystick-wrap {{
                justify-content: center;
                flex-direction: column;
                align-items: center;
            }}
            .joystick-pad {{
                width: 260px;
                height: 260px;
            }}
            .joystick-knob {{
                left: 101px;
                top: 101px;
            }}
            .video-frame {{
                min-height: 200px;
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{robot_name} Control Panel</h1>

        <nav class="mobile-tabs" role="tablist" aria-label="Section navigation">
            <button class="tab-btn active" data-tab="drive" onclick="showTab('drive')">Drive</button>
            <button class="tab-btn" data-tab="camera" onclick="showTab('camera')">Camera</button>
            <button class="tab-btn" data-tab="settings" onclick="showTab('settings')">Settings</button>
        </nav>

        <div class="status">
            <h2>System Status</h2>
            <p>✓ API Service: Running on port {api_port}</p>
            <p>✓ UI Service: Running</p>
            <p>✓ Configuration: Loaded</p>
        </div>

        <div class="section" data-tab="settings">
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

            <div class="form-group">
                <label for="ttsPreviewText">TTS Preview Text:</label>
                <input type="text" id="ttsPreviewText" value="System ready." placeholder="Enter text to speak">
                <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:10px;">
                    <label for="ttsVolume">Volume</label>
                    <input type="range" id="ttsVolume" min="0" max="100" value="80" oninput="updateTtsVolume()">
                    <span id="ttsVolumeValue" class="current-value">80%</span>
                    <label>
                        <input type="checkbox" id="ttsMuted" onchange="updateTtsMute()">
                        <span class="checkbox-label">Mute</span>
                    </label>
                    <button class="button button-secondary" onclick="previewTts()">Preview Speech</button>
                </div>
                <p class="info">Volume and mute controls affect UI playback of server-generated TTS audio.</p>
            </div>
            
            <button class="button" onclick="saveWakeWordConfig()">Save Settings</button>
        </div>

        <div class="section" data-tab="settings">
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

            <div class="form-group" style="margin-top:16px;">
                <label>
                    <input type="checkbox" id="autoUpdateEnabled">
                    <span class="checkbox-label">Enable automatic updates</span>
                </label>
                <p class="info">Automatic updates are opt-in and only install promoted stable releases.</p>
                <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:10px;">
                    <label for="updateChannel">Channel</label>
                    <select id="updateChannel">
                        <option value="stable">Stable (recommended)</option>
                    </select>
                    <label for="autoUpdateSchedule">Daily UTC Time</label>
                    <input type="time" id="autoUpdateSchedule" value="03:00" step="60">
                    <button class="button button-secondary" onclick="saveUpdateConfig()">Save Auto-Update Settings</button>
                </div>
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

        <div class="section" data-tab="settings">
            <h2>Health Telemetry</h2>
            <div id="diagnostics-alert" class="alert"></div>
            <p>Uptime: <span id="healthUptime" class="current-value">Loading...</span></p>
            <p>CPU Temp: <span id="healthCpuTemp" class="current-value">Loading...</span></p>
            <p>Memory Used: <span id="healthMemory" class="current-value">Loading...</span></p>
            <p>Disk Used: <span id="healthDisk" class="current-value">Loading...</span></p>
            <p>API Service: <span id="healthApiService" class="current-value">Loading...</span></p>
            <p>UI Service: <span id="healthUiService" class="current-value">Loading...</span></p>
            <p>Updater Service: <span id="healthUpdaterService" class="current-value">Loading...</span></p>
            <div style="margin-top:12px;">
                <button class="button button-secondary" onclick="downloadDiagnosticsBundle()">Download Diagnostics Bundle</button>
            </div>
            <p class="info">Diagnostics bundles include redacted logs and configuration to support troubleshooting without SSH access.</p>
        </div>

        <div class="section" data-tab="drive">
            <h2>Teleoperation</h2>
            <div id="control-alert" class="alert"></div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px;" class="control-btn-grid">
                <button class="button" onclick="armMotors()">Arm</button>
                <button class="button button-warning" onclick="disarmMotors()">Disarm</button>
                <button class="button button-danger" onclick="engageEstop()">E-Stop</button>
                <button class="button button-secondary" onclick="resetEstop()">Reset E-Stop</button>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px; align-items:center;">
                <label for="followTargetId" style="font-weight:600;">Follow Target ID</label>
                <input id="followTargetId" type="number" min="1" value="1" style="width:90px; padding:8px; border:1px solid #d0d7de; border-radius:6px;" />
                <button class="button" onclick="startFollow()">Start Follow</button>
                <button class="button button-secondary" onclick="stopFollow()">Stop Follow</button>
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
                    <p>Motor Backend: <span id="motorBackendValue" class="current-value">unknown</span></p>
                    <p>Motor Degraded: <span id="motorDegradedValue" class="current-value">no</span></p>
                    <p>Disabled Channels: <span id="motorDisabledChannelsValue" class="current-value">none</span></p>
                    <p>Follow Enabled: <span id="followEnabledValue" class="current-value">no</span></p>
                    <p>Follow Lost Target: <span id="followLostValue" class="current-value">no</span></p>
                    <p>Drive Linear: <span id="linearValue" class="current-value">0.00</span> m/s</p>
                    <p>Drive Angular: <span id="angularValue" class="current-value">0.00</span> rad/s</p>
                    <p class="info">Disconnect or missing heartbeat triggers immediate STOP.</p>
                </div>
            </div>
        </div>

        <div class="section" data-tab="camera">
            <h2>Vision</h2>
            <div class="video-panel">
                <img id="videoStream" class="video-frame" alt="Live camera stream" />
                <p>Stream: <span id="videoStatus" class="current-value">connecting...</span></p>
                <p>FPS: <span id="videoFps" class="current-value">0.0</span></p>
            </div>
            <div style="margin-top: 14px;">
                <h3 style="margin-bottom: 8px; color: #444;">Camera Head</h3>
                <p class="info">Pan/tilt commands are clamped to safe bounds from backend config.</p>
                <div class="form-group">
                    <label for="headPanSlider">Pan (<span id="headPanValue" class="current-value">0.0</span> deg)</label>
                    <input id="headPanSlider" type="range" min="-70" max="70" step="1" value="0" oninput="scheduleHeadCommand()">
                </div>
                <div class="form-group">
                    <label for="headTiltSlider">Tilt (<span id="headTiltValue" class="current-value">0.0</span> deg)</label>
                    <input id="headTiltSlider" type="range" min="-35" max="35" step="1" value="0" oninput="scheduleHeadCommand()">
                </div>
                <button class="button button-secondary" onclick="centerHead()">Center Head</button>
            </div>
        </div>

        <div class="section" data-tab="settings">
            <h2>Conversation</h2>
            <div id="chat-alert" class="alert"></div>
            <div id="chatPanel" style="border:1px solid #d0d7de; border-radius:8px; padding:10px; min-height:140px; max-height:280px; overflow-y:auto; background:#fafafa;"></div>
            <div style="display:flex; gap:10px; margin-top:10px; flex-wrap:wrap; align-items:center;">
                <input type="text" id="chatInput" placeholder="Ask TurboPi a question" style="flex:1; min-width:250px;">
                <button class="button" onclick="sendChatMessage()">Send</button>
            </div>
            <div style="margin-top:10px;">
                <label>
                    <input type="checkbox" id="chatVoiceResponses" checked>
                    <span class="checkbox-label">Speak replies with TTS</span>
                </label>
            </div>
            <p class="info">Conversation responses are isolated from motion control and cannot execute robot movement commands.</p>
        </div>
    </div>

    <script>
        const API_BASE = 'http://' + window.location.hostname + ':{api_port}';
        const WS_BASE = 'ws://' + window.location.hostname + ':{ws_port}';
        const CONTROL_WS_PATH = '/ws/control';
        const VIDEO_STREAM_PATH = '/video/stream';
        const VIDEO_STATS_PATH = '/video/stats';
        const VIDEO_STREAM_SECONDS = 3600;
        let controlSocket = null;
        let heartbeatTimer = null;
        let controlReconnectTimer = null;
        let dragActive = false;
        let controlMaxLinear = 0.5;
        let controlMaxAngular = 1.2;
        let headPanMinDeg = -70;
        let headPanMaxDeg = 70;
        let headTiltMinDeg = -35;
        let headTiltMaxDeg = 35;
        let headCommandTimer = null;
        let videoReconnectTimer = null;
        let videoIdlePolls = 0;
        let ttsVolume = 0.8;
        let ttsMuted = false;

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

        function updateTtsVolume() {{
            const slider = document.getElementById('ttsVolume');
            const pct = Math.max(0, Math.min(100, parseInt(slider.value, 10) || 0));
            ttsVolume = pct / 100.0;
            document.getElementById('ttsVolumeValue').textContent = pct + '%';
        }}

        function updateTtsMute() {{
            ttsMuted = document.getElementById('ttsMuted').checked;
        }}

        async function previewTts() {{
            const text = document.getElementById('ttsPreviewText').value.trim();
            if (!text) {{
                showAlert('Preview text cannot be empty', 'error');
                return;
            }}

            let audioUrl = null;
            try {{
                const response = await fetch(API_BASE + '/voice/tts', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text }}),
                }});

                if (!response.ok) {{
                    const message = await getApiErrorMessage(response, 'Failed to synthesize speech');
                    showAlert(message, 'error');
                    return;
                }}

                const audioBlob = await response.blob();
                audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                audio.volume = ttsVolume;
                audio.muted = ttsMuted;
                audio.onended = () => URL.revokeObjectURL(audioUrl);
                audio.onerror = () => URL.revokeObjectURL(audioUrl);
                await audio.play();
                showAlert('Playing TTS preview', 'success');
            }} catch (error) {{
                if (audioUrl) {{
                    URL.revokeObjectURL(audioUrl);
                }}
                showAlert('TTS preview failed: ' + error.message, 'error');
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

        function showDiagnosticsAlert(message, type) {{
            const alertDiv = document.getElementById('diagnostics-alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
            if (type === 'success') {{
                setTimeout(() => {{ alertDiv.style.display = 'none'; }}, 3000);
            }}
        }}

        function showChatAlert(message, type) {{
            const alertDiv = document.getElementById('chat-alert');
            alertDiv.textContent = message;
            alertDiv.className = 'alert ' + type;
            alertDiv.style.display = 'block';
            if (type === 'success') {{
                setTimeout(() => {{ alertDiv.style.display = 'none'; }}, 3000);
            }}
        }}

        function appendChatMessage(role, text) {{
            const panel = document.getElementById('chatPanel');
            const row = document.createElement('p');
            row.style.margin = '8px 0';
            row.innerHTML = '<strong>' + role + ':</strong> ' + text;
            panel.appendChild(row);
            panel.scrollTop = panel.scrollHeight;
        }}

        async function speakText(text) {{
            let audioUrl = null;
            const response = await fetch(API_BASE + '/voice/tts', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ text: text }}),
            }});
            if (!response.ok) {{
                throw new Error(await getApiErrorMessage(response, 'Failed to synthesize speech'));
            }}

            const audioBlob = await response.blob();
            audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.volume = ttsVolume;
            audio.muted = ttsMuted;
            audio.onended = () => URL.revokeObjectURL(audioUrl);
            audio.onerror = () => URL.revokeObjectURL(audioUrl);
            try {{
                await audio.play();
            }} catch (error) {{
                if (audioUrl) {{
                    URL.revokeObjectURL(audioUrl);
                }}
                throw error;
            }}
        }}

        async function sendChatMessage() {{
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) {{
                showChatAlert('Chat message cannot be empty.', 'error');
                return;
            }}

            appendChatMessage('You', message);
            input.value = '';

            try {{
                const response = await fetch(API_BASE + '/voice/conversation', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ message: message }}),
                }});
                if (!response.ok) {{
                    throw new Error(await getApiErrorMessage(response, 'Conversation request failed'));
                }}

                const data = await response.json();
                appendChatMessage('TurboPi', data.reply || 'No response');

                if (data.guardrail_triggered) {{
                    showChatAlert('Safety guardrail: command-like request blocked in conversation mode.', 'error');
                }} else {{
                    showChatAlert('Reply received.', 'success');
                }}

                if (document.getElementById('chatVoiceResponses').checked && data.reply) {{
                    try {{
                        await speakText(data.reply);
                    }} catch (error) {{
                        showChatAlert('Reply generated but TTS playback failed: ' + error.message, 'error');
                    }}
                }}
            }} catch (error) {{
                showChatAlert('Conversation error: ' + error.message, 'error');
            }}
        }}

        function formatUptime(seconds) {{
            const total = Math.max(0, Math.floor(seconds || 0));
            const hours = Math.floor(total / 3600);
            const minutes = Math.floor((total % 3600) / 60);
            const secs = total % 60;
            return `${{hours}}h ${{minutes}}m ${{secs}}s`;
        }}

        async function refreshSystemStatus() {{
            try {{
                const response = await fetch(API_BASE + '/health');
                if (!response.ok) return;
                const data = await response.json();
                document.getElementById('healthUptime').textContent = formatUptime(data.uptime);
                document.getElementById('healthCpuTemp').textContent =
                    typeof data.cpu_temp === 'number' ? `${{data.cpu_temp.toFixed(1)}} C` : 'n/a';

                const memory = data.memory || {{}};
                const disk = data.disk || {{}};
                const services = data.services || {{}};

                document.getElementById('healthMemory').textContent =
                    (typeof memory.used_mb === 'number' && typeof memory.total_mb === 'number')
                        ? `${{memory.used_mb.toFixed(0)}} / ${{memory.total_mb.toFixed(0)}} MB`
                        : 'n/a';
                document.getElementById('healthDisk').textContent =
                    (typeof disk.used_mb === 'number' && typeof disk.total_mb === 'number')
                        ? `${{disk.used_mb.toFixed(0)}} / ${{disk.total_mb.toFixed(0)}} MB`
                        : 'n/a';
                document.getElementById('healthApiService').textContent = services.api || 'unknown';
                document.getElementById('healthUiService').textContent = services.ui || 'unknown';
                document.getElementById('healthUpdaterService').textContent = services.updater || 'unknown';
            }} catch (error) {{
                // status refresh should stay best-effort
            }}
        }}

        async function downloadDiagnosticsBundle() {{
            try {{
                const response = await fetch(API_BASE + '/diagnostics/bundle');
                if (!response.ok) {{
                    throw new Error('Failed to generate diagnostics bundle');
                }}
                const blob = await response.blob();
                const objectUrl = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = objectUrl;
                link.download = 'turbopi-diagnostics.tar.gz';
                document.body.appendChild(link);
                link.click();
                link.remove();
                setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
                showDiagnosticsAlert('Diagnostics bundle downloaded.', 'success');
            }} catch (error) {{
                showDiagnosticsAlert('Error downloading diagnostics bundle: ' + error.message, 'error');
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

        async function startFollow() {{
            const targetInput = document.getElementById('followTargetId');
            const rawTarget = parseInt(targetInput.value, 10);
            const payload = Number.isFinite(rawTarget) && rawTarget > 0
                ? {{ target_id: rawTarget }}
                : {{}};

            const response = await fetch(API_BASE + '/control/follow/start', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload),
            }});
            const data = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(data.message || 'Failed to start follow mode', 'error');
                return;
            }}
            showControlAlert('Follow mode started', 'success');
            await refreshControlState();
        }}

        async function stopFollow() {{
            const response = await fetch(API_BASE + '/control/follow/stop', {{ method: 'POST' }});
            const data = await parseApiPayload(response);
            if (!response.ok) {{
                showControlAlert(data.message || 'Failed to stop follow mode', 'error');
                return;
            }}
            showControlAlert('Follow mode stopped', 'success');
            await refreshControlState();
        }}

        function scheduleControlReconnect() {{
            if (controlReconnectTimer) return;
            controlReconnectTimer = setTimeout(() => {{
                controlReconnectTimer = null;
                connectControlSocket();
            }}, 1000);
        }}

        function connectControlSocket() {{
            if (controlSocket && (controlSocket.readyState === WebSocket.OPEN || controlSocket.readyState === WebSocket.CONNECTING)) {{
                return;
            }}

            const socket = new WebSocket(WS_BASE + CONTROL_WS_PATH);
            controlSocket = socket;

            socket.onopen = () => {{
                if (controlSocket !== socket) return;
                document.getElementById('wsStatus').textContent = 'connected';
                if (controlReconnectTimer) {{
                    clearTimeout(controlReconnectTimer);
                    controlReconnectTimer = null;
                }}
                if (heartbeatTimer) clearInterval(heartbeatTimer);
                heartbeatTimer = setInterval(() => {{
                    if (controlSocket === socket && socket.readyState === WebSocket.OPEN) {{
                        socket.send(JSON.stringify({{ type: 'heartbeat' }}));
                    }}
                }}, 200);
            }};

            socket.onmessage = (event) => {{
                if (controlSocket !== socket) return;
                try {{
                    const payload = JSON.parse(event.data);
                    if (payload && payload.message === 'inactive_connection') {{
                        if (socket.readyState === WebSocket.OPEN) {{
                            socket.close();
                        }}
                        scheduleControlReconnect();
                    }}
                }} catch (error) {{
                    // Ignore non-JSON websocket responses.
                }}
            }};

            socket.onerror = () => {{
                if (controlSocket !== socket) return;
                document.getElementById('wsStatus').textContent = 'error';
            }};

            socket.onclose = () => {{
                if (controlSocket !== socket) return;
                document.getElementById('wsStatus').textContent = 'disconnected';
                if (heartbeatTimer) {{
                    clearInterval(heartbeatTimer);
                    heartbeatTimer = null;
                }}
                controlSocket = null;
                scheduleControlReconnect();
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

        function setHeadDisplay(panDeg, tiltDeg) {{
            document.getElementById('headPanValue').textContent = panDeg.toFixed(1);
            document.getElementById('headTiltValue').textContent = tiltDeg.toFixed(1);
        }}

        function sendHeadCommand(panDeg, tiltDeg, center = false) {{
            if (!controlSocket || controlSocket.readyState !== WebSocket.OPEN) {{
                showControlAlert('Control websocket is disconnected', 'error');
                return;
            }}
            if (center) {{
                controlSocket.send(JSON.stringify({{ type: 'head', center: true }}));
                return;
            }}
            controlSocket.send(JSON.stringify({{
                type: 'head',
                pan_deg: panDeg,
                tilt_deg: tiltDeg,
            }}));
        }}

        function updateHeadFromSliders(sendNow = false) {{
            const panSlider = document.getElementById('headPanSlider');
            const tiltSlider = document.getElementById('headTiltSlider');
            const panDeg = parseFloat(panSlider.value) || 0;
            const tiltDeg = parseFloat(tiltSlider.value) || 0;
            setHeadDisplay(panDeg, tiltDeg);
            if (!sendNow) {{
                return;
            }}
            sendHeadCommand(panDeg, tiltDeg);
        }}

        function scheduleHeadCommand() {{
            if (headCommandTimer) {{
                clearTimeout(headCommandTimer);
            }}
            headCommandTimer = setTimeout(() => {{
                headCommandTimer = null;
                updateHeadFromSliders(true);
            }}, 60);
        }}

        function centerHead() {{
            const panSlider = document.getElementById('headPanSlider');
            const tiltSlider = document.getElementById('headTiltSlider');
            panSlider.value = 0;
            tiltSlider.value = 0;
            setHeadDisplay(0, 0);
            sendHeadCommand(0, 0, true);
        }}

        function stopJoystick() {{
            const _pad = document.getElementById('joystickPad');
            const _knob = document.getElementById('joystickKnob');
            const _c = Math.floor((_pad.offsetWidth - _knob.offsetWidth) / 2);
            _knob.style.left = _c + 'px';
            _knob.style.top = _c + 'px';
            if (controlSocket && controlSocket.readyState === WebSocket.OPEN) {{
                controlSocket.send(JSON.stringify({{ type: 'stop' }}));
            }}
            document.getElementById('linearValue').textContent = '0.00';
            document.getElementById('angularValue').textContent = '0.00';
        }}

        function setupJoystick() {{
            const pad = document.getElementById('joystickPad');
            const knob = document.getElementById('joystickKnob');

            function updateFromEvent(event) {{
                const center = Math.floor((pad.offsetWidth - knob.offsetWidth) / 2);
                const radius = center;
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

                knob.style.left = (center + dx) + 'px';
                knob.style.top = (center + dy) + 'px';

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
                document.getElementById('motorBackendValue').textContent = data.motor_backend || 'unknown';
                document.getElementById('motorDegradedValue').textContent = data.motor_degraded ? 'yes' : 'no';
                const disabled = Array.isArray(data.motor_disabled_channels) ? data.motor_disabled_channels : [];
                document.getElementById('motorDisabledChannelsValue').textContent = disabled.length ? disabled.join(', ') : 'none';
                if (typeof data.head_pan_min_deg === 'number') {{
                    headPanMinDeg = data.head_pan_min_deg;
                }}
                if (typeof data.head_pan_max_deg === 'number') {{
                    headPanMaxDeg = data.head_pan_max_deg;
                }}
                if (typeof data.head_tilt_min_deg === 'number') {{
                    headTiltMinDeg = data.head_tilt_min_deg;
                }}
                if (typeof data.head_tilt_max_deg === 'number') {{
                    headTiltMaxDeg = data.head_tilt_max_deg;
                }}
                const panSlider = document.getElementById('headPanSlider');
                const tiltSlider = document.getElementById('headTiltSlider');
                panSlider.min = String(headPanMinDeg);
                panSlider.max = String(headPanMaxDeg);
                tiltSlider.min = String(headTiltMinDeg);
                tiltSlider.max = String(headTiltMaxDeg);
                if (typeof data.head_pan_deg === 'number') {{
                    panSlider.value = data.head_pan_deg;
                }}
                if (typeof data.head_tilt_deg === 'number') {{
                    tiltSlider.value = data.head_tilt_deg;
                }}
                setHeadDisplay(parseFloat(panSlider.value) || 0, parseFloat(tiltSlider.value) || 0);
                if (typeof data.max_linear_speed === 'number') {{
                    controlMaxLinear = data.max_linear_speed;
                }}
                if (typeof data.max_angular_speed === 'number') {{
                    controlMaxAngular = data.max_angular_speed;
                }}

                const followResponse = await fetch(API_BASE + '/control/follow/state');
                if (followResponse.ok) {{
                    const followData = await followResponse.json();
                    document.getElementById('followEnabledValue').textContent = followData.enabled ? 'yes' : 'no';
                    document.getElementById('followLostValue').textContent = followData.lost_target ? 'yes' : 'no';
                }}
            }} catch (error) {{
                // Keep UI responsive when API is restarting.
            }}
        }}

        function startVideoStream() {{
            const img = document.getElementById('videoStream');
            const statusEl = document.getElementById('videoStatus');
            const streamUrl = API_BASE + VIDEO_STREAM_PATH + '?seconds=' + VIDEO_STREAM_SECONDS + '&t=' + Date.now();
            videoIdlePolls = 0;
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
                    if (stats.active) {{
                        videoIdlePolls = 0;
                        statusEl.textContent = 'live';
                    }} else {{
                        videoIdlePolls += 1;
                        statusEl.textContent = 'idle';
                        if (videoIdlePolls >= 3) {{
                            videoIdlePolls = 0;
                            startVideoStream();
                        }}
                    }}
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

        async function loadUpdateConfig() {{
            try {{
                const response = await fetch(API_BASE + '/updates/config');
                if (!response.ok) throw new Error('Failed to load update settings');
                const data = await response.json();
                document.getElementById('autoUpdateEnabled').checked = !!data.auto_update;
                document.getElementById('updateChannel').value = (data.channel || 'stable');
                document.getElementById('autoUpdateSchedule').value = (data.schedule_utc || '03:00');
            }} catch (error) {{
                showUpdateAlert('Could not load update settings: ' + error.message, 'error');
            }}
        }}

        async function saveUpdateConfig() {{
            const payload = {{
                auto_update: document.getElementById('autoUpdateEnabled').checked,
                channel: document.getElementById('updateChannel').value,
                schedule_utc: document.getElementById('autoUpdateSchedule').value
            }};

            try {{
                const response = await fetch(API_BASE + '/updates/config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await parseApiPayload(response);
                if (!response.ok) {{
                    throw new Error(data.message || data.error || 'Failed to save update settings');
                }}
                if (data && data.persisted === false) {{
                    showUpdateAlert(
                        'Auto-update settings applied, but could not be written to config.env. Changes may be lost after reboot.',
                        'error'
                    );
                }} else {{
                    showUpdateAlert('Auto-update settings saved.', 'success');
                }}
                await loadUpdateConfig();
            }} catch (error) {{
                showUpdateAlert('Could not save update settings: ' + error.message, 'error');
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
        
        function showTab(tab) {{
            document.querySelectorAll('.tab-btn').forEach(b => {{
                b.classList.toggle('active', b.dataset.tab === tab);
            }});
            document.querySelectorAll('.section[data-tab]').forEach(s => {{
                s.classList.toggle('tab-visible', s.dataset.tab === tab);
            }});
        }}

        // Load configuration when page loads
        window.addEventListener('DOMContentLoaded', () => {{
            loadWakeWordConfig();
            updateTtsVolume();
            updateTtsMute();
            loadVersionInfo();
            loadUpdateConfig();
            connectControlSocket();
            setupJoystick();
            setupVideoPanel();
            updateHeadFromSliders(false);
            refreshControlState();
            refreshSystemStatus();
            setInterval(refreshControlState, 500);
            setInterval(refreshSystemStatus, 5000);
            if (window.innerWidth <= 768) {{
                showTab('drive');
            }}
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
