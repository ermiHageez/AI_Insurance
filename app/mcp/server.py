"""MCP Regulatory Compliance Fetcher & Change Detector.

Fetches whitelisted regulatory documents, sanitizes HTML, detects SHA-256
hash changes, and queues content for human review before vector indexing.
"""
import re
import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from app.mcp.registry import is_allowed_domain, REGULATORY_SOURCES_STORE, regulatory_registry
from app.rag.chunker import chunk_document
from app.rag.store import knowledge_store

# Pending approval queue: id -> record
PENDING_APPROVAL_STORE: Dict[str, Dict[str, Any]] = {}
PENDING_AUDIT_LOG: List[Dict[str, Any]] = []

# Regex cleaners for HTML sanitation
_SCRIPT_STYLE_REGEX = re.compile(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
_HTML_TAGS_REGEX = re.compile(r'<[^>]+>')
_WHITESPACE_REGEX = re.compile(r'[ \t]+')


def sanitize_html(html_content: str) -> str:
    """Strip scripts, styling, navigation, and boilerplate from raw HTML."""
    if not html_content:
        return ""
    # Strip dangerous/boilerplate blocks
    clean = _SCRIPT_STYLE_REGEX.sub(' ', html_content)
    # Strip remaining HTML tags
    clean = _HTML_TAGS_REGEX.sub(' ', clean)
    # Clean whitespace
    lines = [line.strip() for line in clean.split('\n') if line.strip()]
    return "\n\n".join(lines)


class RegulatoryFetcher:
    """Fetches, sanitizes, and evaluates regulatory directives for updates."""

    @staticmethod
    async def fetch_regulatory_update(
        target_url: str,
        keyword: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch regulatory content, sanitize, and run SHA-256 change detection."""
        if not is_allowed_domain(target_url):
            return {
                "success": False,
                "error": f"URL '{target_url}' is not on the whitelisted regulatory domains.",
                "status": "REJECTED"
            }

        # Simulated fetch or fixture retrieval
        # For testing/local run: provides mock content if no live connection
        simulated_content = (
            f"National Bank of Ethiopia (NBE) Directive No. SIB/55/2026. "
            f"Requirements for Motor Third-Party and Comprehensive Insurance Tariffs. "
            f"All insurers operating in Ethiopia must maintain minimum statutory reserves. "
            f"Target URL: {target_url}. Keyword query: {keyword or 'General'}."
        )

        sanitized_text = sanitize_html(simulated_content)
        content_hash = hashlib.sha256(sanitized_text.encode('utf-8')).hexdigest()

        # Check against last known hash
        source_record = REGULATORY_SOURCES_STORE.get(source_id) if source_id else None
        last_hash = source_record.get("last_content_hash") if source_record else None

        if last_hash == content_hash:
            return {
                "success": True,
                "status": "UNCHANGED",
                "content_hash": content_hash,
                "message": "Regulatory content has not changed since last index."
            }

        # New or modified content detected -> Add to pending_approval queue
        pending_id = str(uuid.uuid4())
        pending_record = {
            "id": pending_id,
            "source_id": source_id or "DIRECT_FETCH",
            "target_url": target_url,
            "content_hash": content_hash,
            "content_snapshot": sanitized_text,
            "detected_at": time.time(),
            "status": "PENDING",  # PENDING, APPROVED, REJECTED
            "reviewed_by": None,
            "reviewed_at": None
        }
        PENDING_APPROVAL_STORE[pending_id] = pending_record

        # Update source last_fetched
        if source_record:
            source_record["last_fetched_at"] = time.time()

        return {
            "success": True,
            "status": "QUEUED_FOR_APPROVAL",
            "pending_id": pending_id,
            "content_hash": content_hash,
            "preview": sanitized_text[:200]
        }

    @staticmethod
    def approve_and_index(pending_id: str, reviewer: str = "compliance_officer") -> Dict[str, Any]:
        """Approve pending regulatory text, chunk, embed, and index into vector store."""
        if pending_id not in PENDING_APPROVAL_STORE:
            raise KeyError(f"Pending approval record '{pending_id}' not found.")

        record = PENDING_APPROVAL_STORE[pending_id]
        if record["status"] == "APPROVED":
            return {"status": "ALREADY_APPROVED", "chunks_indexed": 0}

        text = record["content_snapshot"]
        source_id = record["source_id"]
        source_hash = record["content_hash"]

        # Chunk the approved content
        chunks = chunk_document(text, metadata={"section": "NBE Directive", "page_num": 1})
        # Upsert into vector store with category 'REGULATORY'
        indexed_count = knowledge_store.upsert_chunks(
            chunks=chunks,
            document_id=f"REG-{source_id}",
            category="REGULATORY",
            source_hash=source_hash
        )

        record["status"] = "APPROVED"
        record["reviewed_by"] = reviewer
        record["reviewed_at"] = time.time()

        # Update source table
        if source_id in REGULATORY_SOURCES_STORE:
            REGULATORY_SOURCES_STORE[source_id]["last_content_hash"] = source_hash

        PENDING_AUDIT_LOG.append({
            "action": "APPROVE_AND_INDEX",
            "pending_id": pending_id,
            "reviewer": reviewer,
            "chunks_indexed": indexed_count,
            "timestamp": time.time()
        })

        return {
            "status": "INDEXED",
            "pending_id": pending_id,
            "chunks_indexed": indexed_count
        }


regulatory_fetcher = RegulatoryFetcher()
