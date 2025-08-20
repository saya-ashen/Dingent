#!/usr/bin/env python3
"""
Simple web server for the new React-style admin dashboard.
This serves the HTML/JS dashboard and can proxy API calls to the backend.
"""

import os
import http.server
import socketserver
import urllib.request
import urllib.parse
import json
from pathlib import Path

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        dashboard_dir = Path(__file__).parent / "web"
        super().__init__(*args, directory=str(dashboard_dir), **kwargs)
    
    def do_GET(self):
        # If it's an API call, proxy it to the backend
        if self.path.startswith('/api/') or self.path in ['/assistants', '/plugins', '/app_settings', '/logs', '/logs/statistics']:
            self.proxy_to_backend()
        else:
            # Serve static files (HTML, CSS, JS)
            if self.path == '/':
                self.path = '/index.html'
            super().do_GET()
    
    def do_POST(self):
        # Proxy POST requests to the backend
        if self.path.startswith('/api/') or self.path in ['/assistants', '/app_settings']:
            self.proxy_to_backend()
        else:
            self.send_error(404)
    
    def do_DELETE(self):
        # Proxy DELETE requests to the backend
        if self.path.startswith('/api/') or self.path.startswith('/plugins/') or self.path == '/logs':
            self.proxy_to_backend()
        else:
            self.send_error(404)
    
    def proxy_to_backend(self):
        """Proxy API requests to the backend server"""
        backend_url = os.getenv('DING_BACKEND_ADMIN_URL', 'http://127.0.0.1:2024')
        
        try:
            # Prepare the request
            url = f"{backend_url}{self.path}"
            
            # Get request body for POST/PUT requests
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Create the request
            req = urllib.request.Request(url, data=request_body, method=self.command)
            
            # Copy relevant headers
            for header in ['Content-Type', 'Authorization']:
                if header in self.headers:
                    req.add_header(header, self.headers[header])
            
            # Make the request
            with urllib.request.urlopen(req, timeout=120) as response:
                # Copy response status and headers
                self.send_response(response.status)
                for header, value in response.headers.items():
                    if header.lower() not in ['server', 'date']:
                        self.send_header(header, value)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                # Copy response body
                response_body = response.read()
                self.wfile.write(response_body)
                
        except urllib.error.HTTPError as e:
            self.send_error(e.code, explain=str(e))
        except Exception as e:
            print(f"Proxy error: {e}")
            self.send_error(502, explain="Backend connection failed")
    
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

def main():
    port = int(os.getenv('DASHBOARD_PORT', 3001))
    
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"🌐 Dingent Admin Dashboard running at http://localhost:{port}")
        print("📖 Open the URL in your browser to access the new React-based admin interface")
        print("🔄 Use Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Dashboard server stopped")

if __name__ == "__main__":
    main()