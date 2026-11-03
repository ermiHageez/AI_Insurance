"""Regulatory Source Registry.

Validates and manages whitelisted Ethiopian regulatory domains
(National Bank of Ethiopia directives, official proclamations, gazettes).
"""
import time
import uuid
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

# Approved domain suffixes / exact hosts
_ALLOWED_DOMAINS = [
    "nbe.gov.et",
    "gov.et",
    "ethiopian-law.org",
    "localhost",
    "127.0.0.1",
    "test-regulations.local"
]

REGULATORY_SOURCES_STORE: Dict[str, Dict[str, Any]] = {}
SOURCE_AUDIT_LOG: List[Dict[str, Any]] = []


def is_allowed_domain(url: str) -> bool:
    """Check if URL host matches approved Ethiopian regulatory allowlist."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False
        return any(hostname == allowed or hostname.endswith("." + allowed) for allowed in _ALLOWED_DOMAINS)
    except Exception:
        return False


class RegulatorySourceRegistry:
    """Manages trusted regulatory sources with audit logging."""

    @staticmethod
    def register_source(
        url: str,
        name: str,
        registered_by: str = "admin@insurtech.et"
    ) -> Dict[str, Any]:
        """Register a new whitelisted regulatory portal."""
        if not is_allowed_domain(url):
            raise ValueError(f"Domain for URL '{url}' is not on the approved regulatory whitelist.")

        source_id = str(uuid.uuid4())
        record = {
            "id": source_id,
            "url": url,
            "name": name,
            "registered_by": registered_by,
            "registered_at": time.time(),
            "active": True,
            "last_content_hash": None,
            "last_fetched_at": None
        }
        REGULATORY_SOURCES_STORE[source_id] = record

        # Audit entry
        SOURCE_AUDIT_LOG.append({
            "action": "REGISTER_SOURCE",
            "source_id": source_id,
            "url": url,
            "actor": registered_by,
            "timestamp": time.time()
        })

        return record

    @staticmethod
    def list_sources() -> List[Dict[str, Any]]:
        return list(REGULATORY_SOURCES_STORE.values())

    @staticmethod
    def get_source(source_id: str) -> Optional[Dict[str, Any]]:
        return REGULATORY_SOURCES_STORE.get(source_id)


regulatory_registry = RegulatorySourceRegistry()
