#!/bin/bash

echo "Starting Mem0 Backend Server..."
echo "================================"

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source mem0_env/bin/activate

# Install Flask if not already installed
pip install flask flask-cors -q

# Change to backend directory
cd backend

# Start the Flask server
echo "Backend API starting at: http://localhost:5001"
echo "Press Ctrl+C to stop"
python app.py