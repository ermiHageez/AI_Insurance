#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "======================================================================"
echo "          Running InsurTech AI Microservice Automated Test Suite      "
echo "======================================================================"
PYTHONPATH=. .venv/bin/pytest -v tests/

echo ""
echo "======================================================================"
echo "          Running Interactive Local PC Module Verification            "
echo "======================================================================"
PYTHONPATH=. .venv/bin/python3 scripts/verify_local.py
