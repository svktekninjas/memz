#!/bin/bash

echo "========================================"
echo "Starting Mem0 Application Services"
echo "========================================"
echo ""

# Navigate to project root
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to kill process on port
kill_port() {
    local port=$1
    local service=$2
    echo "Checking for existing $service on port $port..."
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "  Found existing process (PID: $pid) on port $port, stopping..."
        kill -9 $pid 2>/dev/null
        sleep 1
    else
        echo "  No existing process found on port $port"
    fi
}

# Function to kill existing Python processes
kill_python_service() {
    local script=$1
    local service=$2
    echo "Checking for existing $service process..."
    local pids=$(ps aux | grep -E "python.*$script" | grep -v grep | awk '{print $2}')
    if [ ! -z "$pids" ]; then
        echo "  Found existing $service processes, stopping..."
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    else
        echo "  No existing $service process found"
    fi
}

# Clean up existing processes
echo "Cleaning up existing processes..."
echo "--------------------------------"
kill_port 5001 "Backend API"
kill_port 5002 "Knowledge Base"
kill_port 8000 "Frontend"
kill_python_service "app.py" "Backend"
kill_python_service "kb_api.py" "Knowledge Base"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source mem0_env/bin/activate

# Start Backend API
echo "Starting Backend API..."
cd backend
nohup python app.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend API started (PID: $BACKEND_PID)"
echo "  Logs: logs/backend.log"
cd ..

# Wait for backend to initialize
sleep 2

# Start Knowledge Base Service
echo ""
echo "Starting Knowledge Base Service..."
cd KnowledgeB
nohup python kb_api.py > ../logs/knowledge_base.log 2>&1 &
KB_PID=$!
echo "  Knowledge Base started (PID: $KB_PID)"
echo "  Logs: logs/knowledge_base.log"
cd ..

# Wait for KB to initialize
sleep 2

# Start Frontend
echo ""
echo "Starting Frontend Server..."
cd web
nohup python -m http.server 8000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  Frontend started (PID: $FRONTEND_PID)"
echo "  Logs: logs/frontend.log"
cd ..

# Save PIDs to file for stop script
echo "$BACKEND_PID" > logs/backend.pid
echo "$KB_PID" > logs/kb.pid
echo "$FRONTEND_PID" > logs/frontend.pid

# Wait for services to fully start
sleep 2

# Check if services are running
echo ""
echo "Verifying services..."
echo "--------------------"

check_service() {
    local port=$1
    local name=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "  ✅ $name is running on port $port"
    else
        echo "  ❌ $name failed to start on port $port"
        echo "     Check logs/$3 for details"
    fi
}

check_service 5001 "Backend API" "backend.log"
check_service 5002 "Knowledge Base" "knowledge_base.log"
check_service 8000 "Frontend" "frontend.log"

echo ""
echo "========================================"
echo "All Services Started Successfully!"
echo "========================================"
echo ""
echo "Service URLs:"
echo "  Frontend:        http://localhost:8000"
echo "  Backend API:     http://localhost:5001"
echo "  Knowledge Base:  http://localhost:5002"
echo ""
echo "Log files:"
echo "  Backend:         logs/backend.log"
echo "  Knowledge Base:  logs/knowledge_base.log"
echo "  Frontend:        logs/frontend.log"
echo ""
echo "To stop all services, run: ./bin/stop_all.sh"
echo "To check status, run: ./utils/status.sh"
echo "To view logs, run: ./utils/view_logs.sh"
echo ""