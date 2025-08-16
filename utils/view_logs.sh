#!/bin/bash

echo "========================================"
echo "Mem0 Application Logs Viewer"
echo "========================================"
echo ""

# Navigate to project root
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT"

# Check if logs directory exists
if [ ! -d "logs" ]; then
    echo "No logs directory found. Services may not have been started yet."
    exit 1
fi

# Function to display menu
show_menu() {
    echo "Select which logs to view:"
    echo "  1) Backend API"
    echo "  2) Knowledge Base"
    echo "  3) Frontend"
    echo "  4) All logs (combined)"
    echo "  5) Follow all logs (real-time)"
    echo "  6) Clear all logs"
    echo "  0) Exit"
    echo ""
    echo -n "Enter your choice: "
}

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            echo ""
            echo "=== Backend API Logs ==="
            if [ -f "logs/backend.log" ]; then
                tail -n 50 logs/backend.log
            else
                echo "No backend logs found"
            fi
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        2)
            echo ""
            echo "=== Knowledge Base Logs ==="
            if [ -f "logs/knowledge_base.log" ]; then
                tail -n 50 logs/knowledge_base.log
            else
                echo "No knowledge base logs found"
            fi
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        3)
            echo ""
            echo "=== Frontend Logs ==="
            if [ -f "logs/frontend.log" ]; then
                tail -n 50 logs/frontend.log
            else
                echo "No frontend logs found"
            fi
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        4)
            echo ""
            echo "=== All Logs (Last 50 lines each) ==="
            echo ""
            for logfile in logs/*.log; do
                if [ -f "$logfile" ]; then
                    echo "--- $(basename $logfile) ---"
                    tail -n 20 "$logfile"
                    echo ""
                fi
            done
            echo "Press Enter to continue..."
            read
            ;;
        5)
            echo ""
            echo "=== Following All Logs (Press Ctrl+C to stop) ==="
            echo ""
            tail -f logs/*.log
            ;;
        6)
            echo ""
            echo -n "Are you sure you want to clear all logs? (y/n): "
            read confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                > logs/backend.log 2>/dev/null
                > logs/knowledge_base.log 2>/dev/null
                > logs/frontend.log 2>/dev/null
                echo "All logs cleared"
            else
                echo "Cancelled"
            fi
            echo ""
            echo "Press Enter to continue..."
            read
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            echo ""
            ;;
    esac
    
    clear
done