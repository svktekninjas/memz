#!/bin/bash

echo "Starting Mem0 Frontend Server..."
echo "================================"

# Navigate to project root
cd "$(dirname "$0")/.."

# Change to web directory
cd web

# Start Python web server with explicit bind to localhost
echo "Frontend starting at: http://localhost:8000"
echo "Press Ctrl+C to stop"
python3 -m http.server 8000 --bind 127.0.0.1