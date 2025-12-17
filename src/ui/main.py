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
from http.server import HTTPServer, SimpleHTTPRequestHandler


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
            
            html = f"""<!DOCTYPE html>
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
        .status {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .info {{
            color: #666;
            text-align: center;
            margin-top: 20px;
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
        <div class="info">
            <p>This is a skeleton implementation.</p>
            <p>Full UI features will be added in future epics.</p>
        </div>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode())
        else:
            self.send_error(404, "Not Found")


def main():
    """Main entry point for the UI service"""
    # Load configuration from environment
    host = os.environ.get('UI_HOST', '0.0.0.0')
    port = int(os.environ.get('UI_PORT', '8081'))
    robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')

    print(f"TurboPi Web UI starting...")
    print(f"Robot Name: {robot_name}")
    print(f"Listening on {host}:{port}")
    print(f"Access UI at: http://{host}:{port}/")

    # Create and start HTTP server
    server = HTTPServer((host, port), UIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down UI service...")
        server.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
