"""Claim Status Tool with IDOR Security Protection.

Validates that the inquiring customer owns the requested claim before returning
stage details. Cross-customer probes return generic not-found and log security events.
"""
import time
import logging
from typing import Dict, Any, Optional

try:
    import structlog
    logger = structlog.get_logger("security.claims")
except ImportError:
    std_logger = logging.getLogger("security.claims")
    class LoggerShim:
        def info(self, msg, **kwargs): std_logger.info(f"{msg} {kwargs}" if kwargs else msg)
        def warn(self, msg, **kwargs): std_logger.warning(f"{msg} {kwargs}" if kwargs else msg)
        def error(self, msg, **kwargs): std_logger.error(f"{msg} {kwargs}" if kwargs else msg)
    logger = LoggerShim()

# In-memory mock claims database for standalone local PC testing
_LOCAL_MOCK_CLAIMS: Dict[str, Dict[str, Any]] = {
    "CLM-1001": {
        "id": "CLM-1001",
        "customerId": "cust-user-123",
        "status": "UNDER_INVESTIGATION",
        "claimType": "MOTOR_ACCIDENT",
        "amount": 45000.00,
        "updatedAt": "2026-10-20T10:30:00Z"
    },
    "CLM-1002": {
        "id": "CLM-1002",
        "customerId": "cust-user-456",
        "status": "APPROVED",
        "claimType": "THIRD_PARTY_PROPERTY",
        "amount": 12000.00,
        "updatedAt": "2026-10-22T14:15:00Z"
    },
    "CLM-1003": {
        "id": "CLM-1003",
        "customerId": "cust-user-123",
        "status": "SETTLED",
        "claimType": "WINDSHIELD_DAMAGE",
        "amount": 8500.00,
        "updatedAt": "2026-10-24T09:00:00Z"
    }
}

# Audit trail for security investigations
SECURITY_EVENT_AUDIT: list[Dict[str, Any]] = []


class ClaimStatusTool:
    """Tool resolving claim status with strict IDOR ownership checks."""

    @staticmethod
    async def get_claim_status(
        claim_number: str,
        caller_customer_id: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch claim status ensuring caller identity matches claim ownership.
        
        Args:
            claim_number: The claim identifier (e.g. "CLM-1001" or numeric ID).
            caller_customer_id: The authenticated user's ID derived from JWT `sub`.
            auth_token: Raw Bearer token for remote platform calls.
            
        Returns:
            Status payload if authorized, or generic rejection.
        """
        clean_claim_id = str(claim_number).strip().upper()
        
        # 1. Lookup claim record (from local mock or remote platform)
        claim_record = _LOCAL_MOCK_CLAIMS.get(clean_claim_id)

        # 2. Unknown claim handling: Return generic message
        if not claim_record:
            return {
                "success": False,
                "error": "Claim not found or unauthorized access",
                "code": "NOT_FOUND_OR_UNAUTHORIZED"
            }

        # 3. IDOR Ownership Verification
        claim_owner = str(claim_record.get("customerId", ""))
        caller_id = str(caller_customer_id).strip()

        if claim_owner != caller_id:
            # SECURITY ALERT: Cross-customer probe detected
            event = {
                "event_type": "UNAUTHORIZED_CLAIM_PROBE",
                "attempted_claim": clean_claim_id,
                "caller_id": caller_id,
                "actual_owner": claim_owner,
                "timestamp": time.time(),
                "action": "DENIED"
            }
            SECURITY_EVENT_AUDIT.append(event)
            logger.warn(
                "Cross-customer claim probe detected and blocked",
                caller=caller_id,
                claim=clean_claim_id
            )
            return {
                "success": False,
                "error": "Claim not found or unauthorized access",
                "code": "NOT_FOUND_OR_UNAUTHORIZED"
            }

        # 4. Authorized Access
        return {
            "success": True,
            "claimId": claim_record["id"],
            "status": claim_record["status"],
            "claimType": claim_record["claimType"],
            "amount": claim_record["amount"],
            "updatedAt": claim_record["updatedAt"]
        }


claim_tool = ClaimStatusTool()
