"""End-to-End FastAPI Endpoint Integration Tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.rag.store import knowledge_store
from app.core.config import settings


@pytest.mark.asyncio
class TestApiEndpoints:

    async def test_health_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Liveness
            res = await ac.get("/healthz")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ok"
            assert data["port"] == 5000
            assert data["service"] == "insuretech-ai"

            # Readiness
            res_ready = await ac.get("/readyz")
            assert res_ready.status_code == 200
            assert res_ready.json()["status"] == "ok"

    async def test_chat_and_disclaimer_flow(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Ingest sample policy text
            upload_files = {
                "file": ("motor_sample.txt", b"Motor policy covers third party property up to 100,000 ETB. Deductible is 2,000 ETB.", "text/plain")
            }
            upload_res = await ac.post("/api/v1/kb/documents/upload", files=upload_files, data={"category": "POLICY"})
            assert upload_res.status_code == 202

            # 2. Ask question
            chat_res = await ac.post(
                "/api/v1/chat/messages",
                json={"message": "What is the deductible for motor policy?"}
            )
            assert chat_res.status_code == 200
            body = chat_res.json()
            assert "reply" in body
            assert settings.ENGLISH_DISCLAIMER in body["reply"] or settings.AMHARIC_DISCLAIMER in body["reply"]
            assert len(body["citations"]) > 0

    async def test_claim_status_idor_flow(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Caller cust-user-123 asking about own claim CLM-1001
            res_authorized = await ac.post(
                "/api/v1/chat/messages",
                headers={"Authorization": "Bearer token-for-cust-user-123"},
                json={"message": "What is the status of claim CLM-1001?"}
            )
            assert res_authorized.status_code == 200
            assert "UNDER_INVESTIGATION" in res_authorized.json()["reply"]

            # Caller cust-user-123 probing cust-user-456's claim CLM-1002
            res_probe = await ac.post(
                "/api/v1/chat/messages",
                headers={"Authorization": "Bearer token-for-cust-user-123"},
                json={"message": "What is the status of claim CLM-1002?"}
            )
            assert res_probe.status_code == 200
            assert "Claim not found or unauthorized access" in res_probe.json()["reply"]
