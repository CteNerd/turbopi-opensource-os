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
    </div>

    <script>
        const API_BASE = 'http://' + window.location.hostname + ':{api_port}';
        
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
        
        // Load configuration when page loads
        window.addEventListener('DOMContentLoaded', loadWakeWordConfig);
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
            
            html = HTML_TEMPLATE.format(robot_name=robot_name, api_port=api_port)
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
