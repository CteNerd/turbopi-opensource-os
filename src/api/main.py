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
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone


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
                # CPU temperature not available on this system
                pass

            # Get version from environment or default
            version = os.environ.get('VERSION', '0.1.0-dev')

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
