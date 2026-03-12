#!/bin/bash
echo "--- Environment Diagnostics ---"
echo "Current Directory: $(pwd)"
echo "Python Version: $(python3 --version)"
echo "Port: $PORT"
echo "PYTHONPATH: $PYTHONPATH"

# Try to start uvicorn in the background and check if it listens
export PYTHONPATH=$PYTHONPATH:.
.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
PID=$!
sleep 5

echo "Checking if port ${PORT:-8000} is listening..."
lsof -i :${PORT:-8000}

echo "Closing diagnostic server..."
kill $PID
