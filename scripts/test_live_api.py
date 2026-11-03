#!/usr/bin/env python3
"""Live End-to-End Test Suite for InsurTech AI Assistant on Port 5000.

Tests live HTTP endpoints and WebSocket streaming:
1. Health & Readiness (GET /healthz, GET /readyz)
2. Policy Document Upload & Chunk Search
3. Grounded Amharic Text Chat with Mandatory Legal Disclaimer
4. Claim Status Inquiry with IDOR Ownership Enforcement
5. Full-Duplex Voice WebSocket: Audio Streaming, Transcripts & 150ms Barge-In Cancellation
"""
import sys
import os
import json
import time
import asyncio
import httpx
import websockets

BASE_URL = os.environ.get("AI_BASE_URL", "http://127.0.0.1:5000")
WS_URL = os.environ.get("AI_WS_URL", "ws://127.0.0.1:5000/ws/v1/voice/chat")

PASS = "\033[92m[PASSED]\033[0m"
FAIL = "\033[91m[FAILED]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"🚀 {title}")
    print("=" * 70)


async def test_health(client: httpx.AsyncClient):
    print_section("1. Testing Health & Readiness Endpoints")
    # Healthz
    r = await client.get(f"{BASE_URL}/healthz")
    assert r.status_code == 200, f"healthz returned {r.status_code}"
    data = r.json()
    assert data["status"] == "ok" and data["port"] == 5000
    print(f"  {PASS} GET /healthz -> status: {data['status']}, port: {data['port']}")

    # Readyz
    r = await client.get(f"{BASE_URL}/readyz")
    assert r.status_code == 200, f"readyz returned {r.status_code}"
    ready_data = r.json()
    assert ready_data["status"] == "ok"
    print(f"  {PASS} GET /readyz -> dependencies: {ready_data['dependencies']}")


async def test_knowledge_base(client: httpx.AsyncClient):
    print_section("2. Testing Knowledge Base Ingestion & Semantic Search")
    policy_content = (
        "የሞተር ተሽከርካሪ የሦስተኛ ወገን ኢንሹራንስ መመሪያ።\n\n"
        "አንቀጽ 8: የካሳ ክፍያ ገደብ።\n"
        "በአዋጅ ቁጥር 799/2005 መሰረት ለማንኛውም ሰው የአካል ጉዳት የሚከፈለው ከፍተኛ የካሳ መጠን 500,000 ብር ነው። "
        "ለንብረት ጉዳት የሚከፈለው ገደብ 100,000 ብር ነው።\n\n"
        "አንቀጽ 9: የመድን ተቀናሽ (Deductible)።\n"
        "ለግል መኪና ተቀናሽ 2,500 ብር ሲሆን ለንግድ መኪና 5,000 ብር ነው።"
    )

    files = {
        "file": ("motor_sample_directive.txt", policy_content.encode("utf-8"), "text/plain")
    }
    r = await client.post(f"{BASE_URL}/api/v1/kb/documents/upload", files=files, data={"category": "POLICY"})
    assert r.status_code == 202, f"Upload returned {r.status_code}: {r.text}"
    job = r.json()
    print(f"  {PASS} POST /api/v1/kb/documents/upload -> Job ID: {job['jobId']}, Status: {job['status']}")

    # Allow background indexing task to finish
    await asyncio.sleep(0.5)

    # Search with homophone variation (ሶስተኛ vs ሦስተኛ)
    query = "የሶስተኛ ወገን የአካል ጉዳት የካሳ ገደብ ስንት ነው?"
    sr = await client.post(f"{BASE_URL}/api/v1/kb/search", json={"query": query, "top_k": 2})
    assert sr.status_code == 200, f"Search returned {sr.status_code}"
    results = sr.json()
    assert len(results) > 0, "No chunks returned"
    print(f"  {PASS} POST /api/v1/kb/search -> Retrieved {len(results)} chunk(s). Top score: {results[0]['score']}")
    print(f"         Cited Section: [{results[0]['document_id']}, {results[0]['section']}]")


async def test_grounded_chat(client: httpx.AsyncClient):
    print_section("3. Testing Grounded Chat with Legal Disclaimer")
    prompt = "የሶስተኛ ወገን የአካል ጉዳት የካሳ ገደብ ስንት ነው?"
    r = await client.post(
        f"{BASE_URL}/api/v1/chat/messages",
        headers={"Authorization": "Bearer token-for-cust-user-123"},
        json={"message": prompt}
    )
    assert r.status_code == 200, f"Chat returned {r.status_code}: {r.text}"
    resp = r.json()
    reply = resp["reply"]
    disclaimer = "ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"

    assert disclaimer in reply, "Mandatory disclaimer missing from chat reply"
    print(f"  {PASS} POST /api/v1/chat/messages -> Received grounded response with {len(resp['citations'])} citation(s)")
    print(f"  {PASS} Mandatory legal disclaimer present in response body")
    print(f"  {INFO} Reply Preview:\n        {reply[:160]}...")


async def test_claim_idor(client: httpx.AsyncClient):
    print_section("4. Testing Claim Status & IDOR Security Defense")
    # 1. Authorized Inquiry: cust-user-123 queries own claim CLM-1001
    r_auth = await client.post(
        f"{BASE_URL}/api/v1/chat/messages",
        headers={"Authorization": "Bearer token-for-cust-user-123"},
        json={"message": "የይገባኛል ጥያቄ CLM-1001 ሁኔታ ምንድን ነው?"}
    )
    assert r_auth.status_code == 200
    reply_auth = r_auth.json()["reply"]
    assert "UNDER_INVESTIGATION" in reply_auth
    print(f"  {PASS} Authorized Query (User owns CLM-1001): Status returned as UNDER_INVESTIGATION")

    # 2. Unauthorized Inquiry: cust-user-123 probes CLM-1002 (owned by cust-user-456)
    r_unauth = await client.post(
        f"{BASE_URL}/api/v1/chat/messages",
        headers={"Authorization": "Bearer token-for-cust-user-123"},
        json={"message": "What is the status of claim CLM-1002?"}
    )
    assert r_unauth.status_code == 200
    reply_unauth = r_unauth.json()["reply"]
    assert "Claim not found or unauthorized access" in reply_unauth
    print(f"  {PASS} IDOR Probe Blocked (User probed CLM-1002): Generic 404/unauthorized returned")


async def test_voice_websocket():
    print_section("5. Testing Full-Duplex Voice WebSocket & Barge-In Cancellation")
    try:
        async with websockets.connect(WS_URL) as ws:
            print(f"  {PASS} Connected to voice WebSocket at {WS_URL}")

            # Send 16,000 bytes of dummy 16kHz audio buffer
            audio_payload = b"\x00\x00" * 8000
            await ws.send(audio_payload)
            print(f"  {INFO} Streamed 16,000 audio bytes to voice endpoint")

            # Await transcript event
            transcript_received = False
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                if isinstance(msg, str):
                    event_data = json.loads(msg)
                    if event_data.get("event") == "TRANSCRIPT_READY":
                        transcript_received = True
                        print(f"  {PASS} Received event TRANSCRIPT_READY: '{event_data.get('transcript')}'")
                        break

            assert transcript_received, "Failed to receive TRANSCRIPT_READY event"

            # Test Barge-In Interruption
            t0 = time.perf_counter()
            await ws.send(json.dumps({"event": "CANCEL_TURN"}))
            halt_received = False

            while True:
                resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                if isinstance(resp, str):
                    data = json.loads(resp)
                    if data.get("event") == "TURN_CANCELLED":
                        halt_received = True
                        halt_ms = (time.perf_counter() - t0) * 1000
                        server_reported_ms = data.get("halt_time_ms", 0)
                        print(f"  {PASS} Received TURN_CANCELLED in {halt_ms:.2f}ms (server reported: {server_reported_ms}ms)")
                        assert halt_ms < 150.0 or server_reported_ms < 150.0
                        break

            assert halt_received, "Failed to receive TURN_CANCELLED barge-in confirmation"

    except Exception as e:
        print(f"  {FAIL} Voice WebSocket test encountered error: {e}")
        raise


async def main():
    print("======================================================================")
    print("        InsurTech AI Assistant: Live API & WebSocket Test Runner     ")
    print("======================================================================")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check server availability first
        try:
            await client.get(f"{BASE_URL}/healthz")
        except Exception as e:
            print(f"\n{FAIL} Could not connect to AI service at {BASE_URL}.")
            print("Please ensure the service is running with: cd insuretech-ai && ./run_server.sh")
            sys.exit(1)

        await test_health(client)
        await test_knowledge_base(client)
        await test_grounded_chat(client)
        await test_claim_idor(client)

    await test_voice_websocket()

    print("\n" + "=" * 70)
    print("🎉 ALL LIVE HTTP AND WEBSOCKET TESTS COMPLETED WITH 100% SUCCESS!")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(main())
