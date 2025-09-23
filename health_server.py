#!/usr/bin/env python3
"""
Simple health check server for Railway deployment
Provides a /health endpoint that Railway can use for health checks
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "telegram-bot"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_health_server():
    """Start the health check server in a separate thread"""
    try:
        port = int(os.environ.get('HEALTH_CHECK_PORT', '8080'))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Health check server started on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start health server: {e}")

if __name__ == "__main__":
    start_health_server()
