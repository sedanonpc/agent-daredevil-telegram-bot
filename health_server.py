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
        try:
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = b'{"status": "healthy", "service": "telegram-bot", "timestamp": "' + str(int(time.time())).encode() + b'"}'
                self.wfile.write(response)
                print(f"✅ Health check successful - {self.path}")
            else:
                self.send_response(404)
                self.end_headers()
                print(f"❌ Health check failed - Invalid path: {self.path}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except:
                pass

    def log_message(self, format, *args):
        # Suppress default logging but allow our custom prints
        pass

def start_health_server():
    """Start the health check server in a separate thread"""
    try:
        # Use Railway's PORT environment variable if available, otherwise 8080
        port = int(os.environ.get('PORT', os.environ.get('HEALTH_CHECK_PORT', '8080')))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"🏥 Health check server started on port {port}")
        print(f"🏥 Health endpoint available at: http://0.0.0.0:{port}/health")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Failed to start health server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_health_server()
