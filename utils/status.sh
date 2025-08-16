#!/bin/bash

echo "========================================"
echo "Mem0 Application Status"
echo "========================================"
echo ""

# Navigate to project root
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# Function to check service status
check_service() {
    local port=$1
    local name=$2
    local pidfile=$3
    
    # Check if service is listening on port
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -ti:$port)
        echo "✅ $name: RUNNING (PID: $pid, Port: $port)"
        
        # Check log file
        if [ -f "$pidfile" ]; then
            local logfile="${pidfile%.pid}.log"
            if [ -f "$logfile" ]; then
                local last_log=$(tail -n 1 "$logfile" 2>/dev/null | cut -c1-60)
                if [ ! -z "$last_log" ]; then
                    echo "   Last log: $last_log..."
                fi
            fi
        fi
    else
        echo "❌ $name: NOT RUNNING (Port: $port)"
    fi
}

# Check each service
echo "Service Status:"
echo "---------------"
check_service 5001 "Backend API    " "logs/backend.pid"
check_service 5002 "Knowledge Base " "logs/kb.pid"
check_service 8000 "Frontend       " "logs/frontend.pid"

# Check log files
echo ""
echo "Log Files:"
echo "----------"
for logfile in logs/*.log; do
    if [ -f "$logfile" ]; then
        size=$(du -h "$logfile" | cut -f1)
        lines=$(wc -l < "$logfile")
        echo "  $(basename $logfile): $size ($lines lines)"
    fi
done

# Check PIDs
echo ""
echo "PID Files:"
echo "----------"
for pidfile in logs/*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo "  $(basename $pidfile): $pid (active)"
        else
            echo "  $(basename $pidfile): $pid (stale)"
        fi
    fi
done

# Memory usage
echo ""
echo "Memory Usage:"
echo "-------------"
for pidfile in logs/*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            service=$(basename "$pidfile" .pid)
            mem=$(ps -o rss= -p $pid 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
            if [ ! -z "$mem" ]; then
                echo "  $service: $mem"
            fi
        fi
    fi
done

echo ""
echo "========================================"
echo ""
echo "Quick Actions:"
echo "  Start all:  ./bin/start_all.sh"
echo "  Stop all:   ./bin/stop_all.sh"
echo "  View logs:  ./utils/view_logs.sh"
echo ""