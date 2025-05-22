#!/usr/bin/env python3
"""
Simple HTTP server to host the WebSocket test client.
Run this script to start a local server for testing the Botify Realtime API.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Default port for the server
PORT = 8090

# Find the test/realtime directory relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
TEST_DIR = SCRIPT_DIR

def start_server(port):
    """Start an HTTP server on the specified port."""
    handler = http.server.SimpleHTTPRequestHandler

    # Change to the test directory
    os.chdir(TEST_DIR)

    print(f"\033[1;32m✓ Starting test client server on port {port}\033[0m")
    print(f"\033[1;36mℹ Directory: {TEST_DIR}\033[0m")
    print(f"\033[1;36mℹ Available at: http://localhost:{port}/\033[0m")
    print(f"\033[1;36mℹ Press Ctrl+C to stop the server\033[0m")

    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print("\033[1;32m✓ Server started\033[0m")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[1;33m! Server stopped by user\033[0m")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"\033[1;31m✗ Port {port} is already in use. Try a different port.\033[0m")
            return False
        raise
    return True

if __name__ == "__main__":
    # Allow specifying a custom port
    custom_port = PORT
    if len(sys.argv) > 1:
        try:
            custom_port = int(sys.argv[1])
        except ValueError:
            print(f"\033[1;31m✗ Invalid port number: {sys.argv[1]}. Using default: {PORT}\033[0m")

    success = start_server(custom_port)
    if not success and custom_port == PORT:
        # Try an alternative port
        alt_port = PORT + 1
        print(f"\033[1;33m! Trying alternative port: {alt_port}\033[0m")
        start_server(alt_port)
