#!/bin/bash

echo "Starting Knowledge Base Service..."
echo "===================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source mem0_env/bin/activate

# Install KB dependencies if needed
pip install PyPDF2 python-docx beautifulsoup4 markdown -q

# Change to KnowledgeB directory
cd KnowledgeB

# Start the Knowledge Base API
echo "Knowledge Base API starting at: http://localhost:5002"
echo "Press Ctrl+C to stop"
python kb_api.py