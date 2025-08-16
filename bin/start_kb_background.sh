#!/bin/bash

echo "Starting Knowledge Base Service in background..."
echo "=============================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source mem0_env/bin/activate

# Install KB dependencies if needed
pip install PyPDF2 python-docx beautifulsoup4 markdown -q

# Change to KnowledgeB directory
cd KnowledgeB

# Start the Knowledge Base API in background
nohup python kb_api.py > ../logs/kb_api.log 2>&1 &
KB_PID=$!

echo "Knowledge Base API started with PID: $KB_PID"
echo "API running at: http://localhost:5002"
echo "Logs available at: logs/kb_api.log"
echo ""
echo "To stop the service, run: kill $KB_PID"