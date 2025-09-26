#!/usr/bin/env python3
"""
Mock vLLM server for testing LLM auto-configuration functionality.
This creates a simple HTTP server that mimics the vLLM OpenAI-compatible API.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class MockVLLMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/v1/models':
            # Mock response for /v1/models endpoint
            response = {
                "object": "list",
                "data": [
                    {
                        "id": "microsoft/DialoGPT-medium",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "vllm"
                    }
                ]
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_mock_server():
    """Start the mock vLLM server in a separate thread"""
    server = HTTPServer(('localhost', 8000), MockVLLMHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print("Mock vLLM server started on http://localhost:8000")
    return server

if __name__ == "__main__":
    server = start_mock_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down mock server...")
        server.shutdown()