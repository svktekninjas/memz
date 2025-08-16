# Utility Scripts

This directory contains utility and monitoring scripts for the Mem0 application.

## Available Utilities

### `status.sh`
Check the status of all services, including:
- Service running status (Backend, Knowledge Base, Frontend)
- Process IDs and ports
- Log file information
- Memory usage

**Usage:**
```bash
./utils/status.sh
```

### `view_logs.sh`
Interactive log viewer with options to:
- View individual service logs
- Follow all logs in real-time
- View combined logs
- Clear log files

**Usage:**
```bash
./utils/view_logs.sh
```

## Core Scripts (in /bin directory)

The main operational scripts are located in the `/bin` directory:
- `start_all.sh` - Start all services
- `stop_all.sh` - Stop all services
- Individual start scripts for each component

## Quick Commands

From the project root:
```bash
# Check status
./utils/status.sh

# View logs interactively
./utils/view_logs.sh

# Tail all logs in real-time
tail -f logs/*.log
```