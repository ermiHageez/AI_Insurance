"""Fake Claims Microservice for Isolated Test Environment.

Simulates the core platform claims microservice on Port 8082.
Seeded with:
  - CLM-1001: Owned by customerA (cust-user-123)
  - CLM-2001: Owned by customerB (cust-user-456)
  - Unknown claims: HTTP 404
"""
import os
import sys
from fastapi import FastAPI, HTTPException, Header, status
from typing import Optional

app = FastAPI(title="Fake Claims Microservice (Test Seam)", version="1.0.0")

SEEDED_CLAIMS = {
    "CLM-1001": {
        "id": "CLM-1001",
        "claimNumber": "CLM-1001",
        "customerId": "cust-user-123",
        "status": "APPROVED",
        "claimType": "THIRD_PARTY_PROPERTY",
        "amount": 15000.00,
        "policyNumber": "POL-ETH-2026-001",
        "updatedAt": "2026-10-22T14:15:00Z"
    },
    "CLM-2001": {
        "id": "CLM-2001",
        "claimNumber": "CLM-2001",
        "customerId": "cust-user-456",
        "status": "UNDER_INVESTIGATION",
        "claimType": "MOTOR_ACCIDENT",
        "amount": 45000.00,
        "policyNumber": "POL-ETH-2026-002",
        "updatedAt": "2026-10-20T10:30:00Z"
    }
}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "fake-claims-service"}


@app.get("/api/v1/claims/{claim_number}")
async def get_claim(
    claim_number: str,
    authorization: Optional[str] = Header(default=None)
):
    key = claim_number.strip().upper()
    if key not in SEEDED_CLAIMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Claim not found", "claimNumber": key}
        )
    return SEEDED_CLAIMS[key]


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("FAKE_CLAIMS_PORT", 8082))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
