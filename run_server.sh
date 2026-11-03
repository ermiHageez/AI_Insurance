#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "======================================================================"
echo "      Starting InsurTech AI Microservice on Port 5000 (Local Dev)    "
echo "======================================================================"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH=.
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
