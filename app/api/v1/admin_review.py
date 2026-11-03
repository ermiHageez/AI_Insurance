"""Admin Review Desk, Golden-KB Promotion & PII-Safe Training Export."""
import json
import time
from typing import Optional, List

try:
    from fastapi import APIRouter, HTTPException, Response
    from pydantic import BaseModel, Field
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: any):
            self.status_code = status_code
            self.detail = detail
            super().__init__(str(detail))

    class Response:
        def __init__(self, content, media_type="", headers=None, status_code=200):
            self.body = content.encode("utf-8") if isinstance(content, str) else content
            self.status_code = status_code
            self.headers = headers or {}

    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items(): setattr(self, k, v)
    def Field(*args, **kwargs): return None

from app.core.session_memory import CHAT_INTERACTIONS_STORE
from app.core.pii_scrubber import contains_pii
from app.rag.store import knowledge_store
from app.rag.chunker import chunk_document

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Review & Export"])


class PromoteRequest(BaseModel):
    corrected_answer: str = Field(..., description="Expert corrected Amharic/English answer")
    reviewer: str = Field(default="insurance_specialist@insurtech.et")


@router.get("/review/interactions")
async def list_interactions_for_review(rating: Optional[str] = None):
    """List interactions, filterable by rating (e.g. DOWN)."""
    results = []
    for rec in CHAT_INTERACTIONS_STORE.values():
        if rating and rec.get("rating") != rating.upper():
            continue
        results.append(rec)
    
    # Sort newest first
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results


@router.post("/review/interactions/{interaction_id}/promote")
async def promote_to_golden_kb(interaction_id: str, request: PromoteRequest):
    """Promote expert-corrected answer to Golden Knowledge Base (category GOLDEN_QA)."""
    if interaction_id not in CHAT_INTERACTIONS_STORE:
        raise HTTPException(status_code=404, detail="Interaction not found")

    rec = CHAT_INTERACTIONS_STORE[interaction_id]
    original_prompt = rec["scrubbed_prompt"]
    corrected = request.corrected_answer.strip()

    # Create synthetic Q&A document
    qa_text = f"ጥያቄ: {original_prompt}\n\nመልስ: {corrected}"
    doc_id = f"GOLDEN-{interaction_id[:8]}"

    chunks = chunk_document(qa_text, metadata={"section": "Verified FAQ", "page_num": 1})
    indexed = knowledge_store.upsert_chunks(
        chunks=chunks,
        document_id=doc_id,
        category="GOLDEN_QA",
        source_hash=f"golden-{interaction_id}"
    )

    rec["promoted_to_golden"] = True
    rec["golden_doc_id"] = doc_id
    rec["golden_at"] = time.time()
    rec["golden_reviewer"] = request.reviewer

    return {
        "status": "PROMOTED_TO_GOLDEN_KB",
        "document_id": doc_id,
        "chunks_indexed": indexed
    }


@router.get("/export/training-data")
async def export_training_data():
    """Export scrubbed conversations in ShareGPT / OpenAI JSONL format.
    
    CRITICAL COMPLIANCE GATE:
    Runs an independent PII scan over the entire payload before delivery.
    If ANY unredacted phone, Kebele ID, bank account, or TIN is detected,
    refuses export with HTTP 422.
    """
    jsonl_lines = []

    # Group interactions by session_id
    sessions: dict[str, list] = {}
    for rec in CHAT_INTERACTIONS_STORE.values():
        sid = rec["session_id"]
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append(rec)

    for sid, turns in sessions.items():
        conversation_turns = []
        for t in turns:
            conversation_turns.append({"from": "human", "value": t["scrubbed_prompt"]})
            conversation_turns.append({"from": "gpt", "value": t["scrubbed_response"]})

        entry = {
            "session_id": sid,
            "conversations": conversation_turns
        }
        jsonl_lines.append(json.dumps(entry, ensure_ascii=False))

    full_payload = "\n".join(jsonl_lines)

    # DEFENSE-IN-DEPTH: Automated PII Validator Gate
    has_pii, detected_categories = contains_pii(full_payload)
    if has_pii:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "PII_VALIDATION_FAILED",
                "message": "Export aborted: detected unscrubbed customer personal identifiers.",
                "detected_categories": detected_categories
            }
        )

    return Response(
        content=full_payload,
        media_type="application/x-jsonlines",
        headers={
            "Content-Disposition": "attachment; filename=insurtech_ai_training_data.jsonl"
        }
    )
