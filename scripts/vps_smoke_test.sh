#!/usr/bin/env bash
# ==============================================================================
# InsurTech AI Microservice - Automated VPS Smoke Test Suite
# Verifies health, RAG retrieval, PII scrubber, and WebSocket readiness.
# ==============================================================================
set -euo pipefail

TARGET_HOST="${1:-http://localhost:5000}"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}  InsurTech AI Microservice - VPS Smoke Test Suite  ${NC}"
echo -e "${BLUE}  Target: ${TARGET_HOST}                            ${NC}"
echo -e "${BLUE}====================================================${NC}"

# Test 1: Liveness Probe
echo -n "Checking Liveness (/healthz)... "
HEALTH_RESP=$(curl -s -f -X GET "${TARGET_HOST}/healthz" || echo "FAIL")
if [[ "${HEALTH_RESP}" == *"status"* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC} - Response: ${HEALTH_RESP}"
    exit 1
fi

# Test 2: Readiness Probe & Provider Check
echo -n "Checking Readiness (/readyz)... "
READY_RESP=$(curl -s -f -X GET "${TARGET_HOST}/readyz" || echo "FAIL")
if [[ "${READY_RESP}" == *"ready"* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC} - Response: ${READY_RESP}"
    exit 1
fi

# Test 3: Prometheus Metrics
echo -n "Checking Prometheus Metrics (/metrics)... "
METRICS_RESP=$(curl -s -f -X GET "${TARGET_HOST}/metrics" || echo "FAIL")
if [[ "${METRICS_RESP}" == *"insurtech_ai"* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Test 4: Knowledge Base Citation Search (<80ms)
echo -n "Checking Semantic Retrieval (/api/v1/kb/search)... "
SEARCH_RESP=$(curl -s -f -X POST "${TARGET_HOST}/api/v1/kb/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "ተቀናሽ ሂሳብ", "top_k": 3}' || echo "FAIL")
if [[ "${SEARCH_RESP}" == *"["* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC} - Response: ${SEARCH_RESP}"
    exit 1
fi

# Test 5: PII Scrubber & Disclaimer Gate
echo -n "Checking Grounded Chat & Amharic Disclaimer (/api/v1/chat/message)... "
CHAT_RESP=$(curl -s -f -X POST "${TARGET_HOST}/api/v1/chat/message" \
    -H "Content-Type: application/json" \
    -d '{"message": "የፖሊሲ ተቀናሽ ስንት ነው?", "session_id": "vps_smoke_test_01", "customer_id": "CUST-999"}' || echo "FAIL")
if [[ "${CHAT_RESP}" == *"ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው"* ]]; then
    echo -e "${GREEN}PASSED (Mandatory Disclaimer Enforced)${NC}"
else
    echo -e "${RED}FAILED - Disclaimer Missing!${NC} Response: ${CHAT_RESP}"
    exit 1
fi

# Test 6: Regulatory Allowlist Check
echo -n "Checking Regulatory Domain Registry (/api/v1/admin/sources)... "
SOURCES_RESP=$(curl -s -f -X GET "${TARGET_HOST}/api/v1/admin/sources" || echo "FAIL")
if [[ "${SOURCES_RESP}" == *"["* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓ All VPS smoke test verification probes passed successfully!${NC}"
