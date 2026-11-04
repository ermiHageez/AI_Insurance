"""Security Gate Test Suite for Authentication & Authorization.

Targeting findings AUD-B-01, AUD-B-02, AUD-B-03, and AUD-B-04 from AUDIT_REPORT.md.
Known vulnerabilities that will be fixed in Phase 0 are marked as xfail.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from scripts.dev_token_issuer import issue_token


@pytest.mark.security
@pytest.mark.asyncio
async def test_valid_token_authenticated_query():
    """Verify that a validly signed token is accepted for chat."""
    token = issue_token("customerA", "valid")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የሦስተኛ ወገን ኢንሹራንስ የካሳ ገደብ ስንት ነው?"},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው" in data["reply"]


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-02: Missing auth header defaults to cust-user-123 instead of rejecting with HTTP 401", strict=True)
async def test_unauthenticated_request_must_be_rejected():
    """Requests with no Authorization header must be rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"}
        )
    # Expected in Phase 0: 401 Unauthorized
    assert resp.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-01: Expired token accepted because exp claim is not verified", strict=True)
async def test_expired_token_must_be_rejected():
    """Tokens with expired timestamp must be rejected with HTTP 401."""
    token = issue_token("customerA", "expired")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-01: Untrusted secret accepted because JWT signature is unverified", strict=True)
async def test_wrong_signature_must_be_rejected():
    """Tokens signed with wrong secret must be rejected with HTTP 401."""
    token = issue_token("customerA", "wrong_signature")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-01: alg=none token accepted because algorithm whitelist is missing", strict=True)
async def test_alg_none_token_must_be_rejected():
    """Unsigned tokens with alg=none must be rejected with HTTP 401."""
    token = issue_token("customerA", "alg_none")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 401


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-03: Admin endpoints have no authentication dependency", strict=True)
async def test_admin_export_must_reject_unauthenticated():
    """Admin export route must reject unauthenticated requests with 401/403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/export/training-data")
    assert resp.status_code in (401, 403)


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.xfail(reason="AUD-B-02: Token substring match fails on base64 JWT payload, falling back to cust-user-123", strict=True)
async def test_idor_cross_customer_probe_blocked():
    """Customer B attempting to read Customer A's claim CLM-1001 must be blocked."""
    token_b = issue_token("customerB", "valid")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json={"message": "የይገባኛል ጥያቄ CLM-1001 ያለበት ሁኔታ ምንድን ነው?"},
            headers={"Authorization": f"Bearer {token_b}"}
        )
    assert resp.status_code == 200
    reply = resp.json()["reply"]
    # Must NOT reveal amount or status of CLM-1001
    assert "15,000" not in reply
    assert "APPROVED" not in reply
    assert ("አልተገኘም" in reply or "unauthorized" in reply.lower() or "ፈቃድ የለዎትም" in reply)
