#!/bin/bash
# Start script for ReturnShield AI backend
export PYTHONPATH=$PYTHONPATH:.
exec ./.venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
