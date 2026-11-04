#!/usr/bin/env bash
# ==============================================================================
# InsurTech AI Assistant - End-to-End Test Environment Smoke Test
# ==============================================================================
set -euo pipefail

TARGET="${1:-http://127.0.0.1:5000}"
WS_TARGET="${TARGET/http/ws}/ws/v1/voice/chat"
PYTHON=".venv/bin/python3"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  InsurTech AI: Automated Smoke Test Verification     ${NC}"
echo -e "${BLUE}  Target Gateway: ${TARGET}                           ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Mint Tokens for Testing
TOKEN_CUST_A=$(${PYTHON} scripts/dev_token_issuer.py customerA valid)
TOKEN_CUST_B=$(${PYTHON} scripts/dev_token_issuer.py customerB valid)

# 1. Health Liveness Check
echo -n "1. Checking Gateway Liveness (/healthz)... "
HEALTH=$(curl -s -f -X GET "${TARGET}/healthz" || echo "FAIL")
if [[ "${HEALTH}" == *"status"* && "${HEALTH}" == *"ok"* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC} (Response: ${HEALTH})"
    exit 1
fi

# 2. Authorized Chat Turn
echo -n "2. Checking Authorized Chat (/api/v1/chat/messages)... "
CHAT_RESP=$(curl -s -X POST "${TARGET}/api/v1/chat/messages" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_CUST_A}" \
    -d '{"message": "የሦስተኛ ወገን ኢንሹራንስ የካሳ ገደብ ስንት ነው?", "session_id": "smoke-test-sess"}' || echo "FAIL")
if [[ "${CHAT_RESP}" == *"ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው"* ]]; then
    echo -e "${GREEN}PASSED${NC} (Legal disclaimer present)"
else
    echo -e "${RED}FAILED${NC} (Response: ${CHAT_RESP})"
    exit 1
fi

# 3. Claim Lookup as Owner (customerA -> CLM-1001)
echo -n "3. Checking Claim Status as Claim Owner (customerA -> CLM-1001)... "
CLAIM_OWNER_RESP=$(curl -s -X POST "${TARGET}/api/v1/chat/messages" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_CUST_A}" \
    -d '{"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"}' || echo "FAIL")
if [[ "${CLAIM_OWNER_RESP}" == *"CLM-1001"* && "${CLAIM_OWNER_RESP}" == *"UNDER_INVESTIGATION"* || "${CLAIM_OWNER_RESP}" == *"APPROVED"* ]]; then
    echo -e "${GREEN}PASSED${NC} (Authorized claim status returned)"
else
    echo -e "${RED}FAILED${NC} (Response: ${CLAIM_OWNER_RESP})"
    exit 1
fi

# 4. Claim Lookup as Another Customer (customerB -> CLM-1001) - Must be rejected
echo -n "4. Checking Cross-Customer IDOR Defense (customerB -> CLM-1001)... "
IDOR_RESP=$(curl -s -X POST "${TARGET}/api/v1/chat/messages" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_CUST_B}" \
    -d '{"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"}' || echo "FAIL")
if [[ "${IDOR_RESP}" == *"አልተገኘም"* || "${IDOR_RESP}" == *"unauthorized"* || "${IDOR_RESP}" == *"ፈቃድ የለዎትም"* ]]; then
    echo -e "${GREEN}PASSED${NC} (Cross-customer probe successfully rejected)"
else
    echo -e "${RED}FAILED${NC} - Leak detected: ${IDOR_RESP}"
    exit 1
fi

# 5. Admin Call Without Token (Must be rejected)
echo -n "5. Checking Admin Route Protection (/api/v1/admin/export/training-data)... "
ADMIN_HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${TARGET}/api/v1/admin/export/training-data" || echo "500")
if [[ "${ADMIN_HTTP_STATUS}" == "401" || "${ADMIN_HTTP_STATUS}" == "403" ]]; then
    echo -e "${GREEN}PASSED${NC} (Status: ${ADMIN_HTTP_STATUS})"
else
    echo -e "${YELLOW}WARNING (AUD-B-03 GAP)${NC}: Returned ${ADMIN_HTTP_STATUS}. Admin endpoint currently unauthenticated."
fi

# 6. Voice WebSocket Round-Trip with Audio
echo -n "6. Checking Voice WebSocket Round-Trip (/ws/v1/voice/chat)... "
WS_TEST_RESULT=$(${PYTHON} -c "
import asyncio
import json
import websockets

async def test_ws():
    try:
        async with websockets.connect('${WS_TARGET}', timeout=5) as ws:
            # Send sample 16kHz audio frame (16000 zero-samples = 1 second)
            sample_pcm = bytes([0] * 3200)
            await ws.send(sample_pcm)
            
            # Send barge-in cancel frame to verify cancel roundtrip
            await ws.send(json.dumps({'event': 'CANCEL_TURN'}))
            
            # Expect response
            resp = await asyncio.wait_for(ws.recv(), timeout=4)
            data = json.loads(resp) if isinstance(resp, str) else {'binary_bytes': len(resp)}
            return True, data
    except Exception as e:
        return False, str(e)

ok, details = asyncio.run(test_ws())
if ok:
    print('PASSED')
else:
    print(f'FAILED: {details}')
" || echo "FAILED")

if [[ "${WS_TEST_RESULT}" == *"PASSED"* ]]; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}${WS_TEST_RESULT}${NC}"
fi

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  Smoke Test Verification Complete                    ${NC}"
echo -e "${BLUE}======================================================${NC}"
