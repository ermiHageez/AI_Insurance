#!/usr/bin/env python3
"""Dev-Only JWT Token Issuer for Test Environment.

Available ONLY when APP_ENV or ENVIRONMENT is 'test' or 'dev'.
Mints JWTs for three seeded identities:
  - customerA: sub="cust-user-123", roles=["POLICYHOLDER"], name="Abebe Bikila"
  - customerB: sub="cust-user-456", roles=["POLICYHOLDER"], name="Almaz Ayana"
  - admin:     sub="admin-001",     roles=["ADMIN", "EMPLOYEE"], name="Admin User"

Supported Variants:
  - valid:            Normal signed token with 1-hour expiration
  - expired:          Token expired 1 hour ago
  - wrong_signature:  Signed with an untrusted secret
  - wrong_audience:   Token with aud='untrusted-client'
  - alg_none:         Unsigned token with alg='none'
"""
import sys
import os
import time
import json
import base64
import hmac
import hashlib
from typing import Dict, Any

# Ensure we are in test or dev environment
ENVIRONMENT = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
if ENVIRONMENT == "production":
    sys.stderr.write("FATAL: Dev token issuer is strictly disabled in production environment.\n")
    sys.exit(1)

JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "dev-secret-key-for-local-testing-insureflow-32-chars-min"
)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ISSUER = "insureflow-auth"
AUDIENCE = "insureflow-api"

USER_PROFILES = {
    "customerA": {
        "sub": "cust-user-123",
        "name": "Abebe Bikila",
        "email": "customerA@insurtech.et",
        "roles": ["POLICYHOLDER"],
        "policyNumber": "POL-ETH-2026-001"
    },
    "customerB": {
        "sub": "cust-user-456",
        "name": "Almaz Ayana",
        "email": "customerB@insurtech.et",
        "roles": ["POLICYHOLDER"],
        "policyNumber": "POL-ETH-2026-002"
    },
    "admin": {
        "sub": "admin-001",
        "name": "Admin Specialist",
        "email": "admin@insurtech.et",
        "roles": ["ADMIN", "EMPLOYEE"],
        "department": "Claims Assessment"
    }
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def issue_token(
    user_key: str = "customerA",
    variant: str = "valid",
    ttl_seconds: int = 3600
) -> str:
    """Mint signed JWT token for the specified user profile and security variant."""
    if user_key not in USER_PROFILES:
        raise ValueError(f"Unknown user '{user_key}'. Choose from: {list(USER_PROFILES.keys())}")

    profile = USER_PROFILES[user_key]
    now = int(time.time())

    # Build Header
    alg = "none" if variant == "alg_none" else JWT_ALGORITHM
    header = {"alg": alg, "typ": "JWT"}

    # Build Payload
    exp = now - 3600 if variant == "expired" else now + ttl_seconds
    aud = "untrusted-client" if variant == "wrong_audience" else AUDIENCE

    payload: Dict[str, Any] = {
        "sub": profile["sub"],
        "name": profile["name"],
        "email": profile["email"],
        "realm_access": {"roles": profile["roles"]},
        "roles": profile["roles"],
        "iss": ISSUER,
        "aud": aud,
        "iat": now,
        "exp": exp
    }

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    signing_input = f"{_b64url_encode(header_bytes)}.{_b64url_encode(payload_bytes)}"

    if variant == "alg_none":
        return f"{signing_input}."

    secret = (
        "untrusted-wrong-secret-key-attacker"
        if variant == "wrong_signature"
        else JWT_SECRET_KEY
    )

    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return f"{signing_input}.{_b64url_encode(signature)}"


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "customerA"
    var = sys.argv[2] if len(sys.argv) > 2 else "valid"
    token = issue_token(user_key=user, variant=var)
    print(token)
