#!/bin/bash

echo "========================================"
echo "Stopping Mem0 Application Services"
echo "========================================"
echo ""

# Navigate to project root
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# Function to stop service by PID file
stop_by_pid_file() {
    local pidfile=$1
    local service=$2
    
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping $service (PID: $pid)..."
            kill -9 $pid 2>/dev/null
            rm "$pidfile"
            echo "  $service stopped"
        else
            echo "$service not running (stale PID file)"
            rm "$pidfile"
        fi
    else
        echo "$service PID file not found"
    fi
}

# Function to kill process on port (fallback)
kill_port() {
    local port=$1
    local service=$2
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Stopping $service on port $port (PID: $pid)..."
        kill -9 $pid 2>/dev/null
        echo "  $service stopped"
    fi
}

# Stop services using PID files
echo "Stopping services using PID files..."
echo "------------------------------------"
stop_by_pid_file "logs/backend.pid" "Backend API"
stop_by_pid_file "logs/kb.pid" "Knowledge Base"
stop_by_pid_file "logs/frontend.pid" "Frontend"

# Additional cleanup - kill any remaining processes on ports
echo ""
echo "Performing additional cleanup..."
echo "--------------------------------"
kill_port 5001 "Backend API"
kill_port 5002 "Knowledge Base"
kill_port 8000 "Frontend"

# Kill any remaining Python processes
echo ""
echo "Cleaning up any remaining Python processes..."
pids=$(ps aux | grep -E "python.*(app\.py|kb_api\.py|http\.server 8000)" | grep -v grep | awk '{print $2}')
if [ ! -z "$pids" ]; then
    echo "  Found remaining processes, stopping..."
    echo "$pids" | xargs kill -9 2>/dev/null
    echo "  Processes stopped"
else
    echo "  No remaining processes found"
fi

echo ""
echo "========================================"
echo "All Services Stopped"
echo "========================================"
echo ""
echo "Log files are preserved in: logs/"
echo "To restart services, run: ./bin/start_all.sh"
echo ""