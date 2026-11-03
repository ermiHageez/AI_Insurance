"""Unit Tests for Claim Status IDOR Defense & Security Audit Logging."""
try:
    import pytest
except ImportError:
    class MockMark:
        def asyncio(self, f): return f
    class MockPytest:
        mark = MockMark()
    pytest = MockPytest()
from app.tools.claims import claim_tool, SECURITY_EVENT_AUDIT


@pytest.mark.asyncio
class TestClaimIdorSecurity:

    async def test_authorized_owner_access(self):
        # Claim CLM-1001 is owned by cust-user-123
        result = await claim_tool.get_claim_status(
            claim_number="CLM-1001",
            caller_customer_id="cust-user-123"
        )
        assert result["success"] is True
        assert result["claimId"] == "CLM-1001"
        assert result["status"] == "UNDER_INVESTIGATION"
        assert result["amount"] == 45000.00

    async def test_cross_customer_probe_blocked(self):
        # Claim CLM-1002 is owned by cust-user-456
        # Caller is cust-user-123 (Attacker / Unauthorized user)
        initial_audit_count = len(SECURITY_EVENT_AUDIT)

        result = await claim_tool.get_claim_status(
            claim_number="CLM-1002",
            caller_customer_id="cust-user-123"
        )

        # Must return generic error to prevent enumeration
        assert result["success"] is False
        assert result["error"] == "Claim not found or unauthorized access"
        assert result["code"] == "NOT_FOUND_OR_UNAUTHORIZED"

        # Security event must be recorded in the audit trail
        assert len(SECURITY_EVENT_AUDIT) > initial_audit_count
        latest_event = SECURITY_EVENT_AUDIT[-1]
        assert latest_event["event_type"] == "UNAUTHORIZED_CLAIM_PROBE"
        assert latest_event["caller_id"] == "cust-user-123"
        assert latest_event["attempted_claim"] == "CLM-1002"
        assert latest_event["action"] == "DENIED"

    async def test_nonexistent_claim_returns_same_generic_error(self):
        result = await claim_tool.get_claim_status(
            claim_number="CLM-9999",
            caller_customer_id="cust-user-123"
        )
        assert result["success"] is False
        assert result["error"] == "Claim not found or unauthorized access"
