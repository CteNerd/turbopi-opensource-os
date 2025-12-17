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
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


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
                pass

            # Get version from environment or default
            version = os.environ.get('VERSION', '0.1.0-dev')

            health_data = {
                'status': 'ok',
                'uptime': uptime,
                'cpu_temp': cpu_temp,
                'version': version,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode())
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")


def main():
    """Main entry point for the API service"""
    # Load configuration from environment
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', '8080'))
    robot_name = os.environ.get('ROBOT_NAME', 'TurboPi')

    print(f"TurboPi API Backend starting...")
    print(f"Robot Name: {robot_name}")
    print(f"Listening on {host}:{port}")
    print(f"Health endpoint: http://{host}:{port}/health")

    # Create and start HTTP server
    server = HTTPServer((host, port), APIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down API service...")
        server.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
