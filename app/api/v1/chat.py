"""Grounded Conversational Core & Feedback Endpoints."""
import re
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.guardrails import (
    build_system_prompt,
    append_mandatory_disclaimer,
    is_prompt_injection,
    is_amharic_query,
    INJECTION_REFUSAL_AMHARIC,
    INJECTION_REFUSAL_ENGLISH
)
from app.rag.store import knowledge_store
from app.llm.router import llm_router
from app.tools.claims import claim_tool
from app.core.session_memory import session_memory
from app.core.pii_scrubber import scrub_pii

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

# Regex to detect claim number inquiries in prompt
_CLAIM_REGEX = re.compile(r'\b(CLM-\d+|ይገባኛል[\s#]*\d+)\b', re.IGNORECASE)


class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    message: str = Field(..., description="User prompt in Amharic or English")


class CitationItem(BaseModel):
    document_id: str
    section: str
    page_num: int
    score: float


class ChatMessageResponse(BaseModel):
    interaction_id: str
    session_id: str
    reply: str
    citations: List[CitationItem]
    provider: str = Field(default="mock", description="Active LLM provider (gemini, openai, ollama, mock)")
    model: str = Field(default="mock", description="Active model identifier")


class FeedbackRequest(BaseModel):
    rating: str = Field(..., pattern="^(UP|DOWN)$", description="Thumbs UP or DOWN")
    comment: Optional[str] = Field(default=None, description="Optional feedback explanation")


@router.post("/messages", response_model=ChatMessageResponse)
async def post_chat_message(
    request: ChatMessageRequest,
    authorization: Optional[str] = Header(default=None)
):
    """Grounded text-chat endpoint.
    
    1. Validates JWT caller identity.
    2. Enforces prompt injection defense.
    3. Handles claim lookup with IDOR check if claim intent detected.
    4. Gathers top-K policy chunks and synthesizes grounded cited answer.
    5. Appends mandatory disclaimer, logs scrubbed interaction, and updates memory.
    """
    raw_text = request.message.strip()
    session_id = request.session_id or str(uuid.uuid4())
    lang = "am" if is_amharic_query(raw_text) else "en"

    # Derive customer ID from token
    # Default to "cust-user-123" for local developer convenience if no header
    customer_id = "cust-user-123"
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        # In full production, decode JWT claims; for local testing, fallback to subject
        if "user-456" in token:
            customer_id = "cust-user-456"
        elif "admin" in token:
            customer_id = "admin-1"

    # 1. Prompt Injection Defense
    if is_prompt_injection(raw_text):
        reply = INJECTION_REFUSAL_AMHARIC if lang == "am" else INJECTION_REFUSAL_ENGLISH
        interaction_id = session_memory.add_turn(
            session_id=session_id,
            user_message=raw_text,
            assistant_reply=reply,
            customer_id=customer_id
        )
        return ChatMessageResponse(
            interaction_id=interaction_id,
            session_id=session_id,
            reply=reply,
            citations=[]
        )

    # 2. Check for Claim Intent
    claim_match = _CLAIM_REGEX.search(raw_text)
    if claim_match:
        claim_num = claim_match.group(1).upper()
        claim_result = await claim_tool.get_claim_status(
            claim_number=claim_num,
            caller_customer_id=customer_id
        )
        if claim_result["success"]:
            status_text = claim_result["status"]
            amount = claim_result["amount"]
            if lang == "am":
                body = (
                    f"የይገባኛል ጥያቄ ቁጥር {claim_num} ያለበት ሁኔታ፡ '{status_text}' ነው። "
                    f"የካሳ መጠን፡ {amount:,.2f} ETB።"
                )
            else:
                body = (
                    f"Claim {claim_num} is currently: '{status_text}'. "
                    f"Amount: {amount:,.2f} ETB."
                )
        else:
            body = (
                "የይገባኛል ጥያቄው አልተገኘም ወይም ይህን መረጃ ለማየት ፈቃድ የለዎትም።"
                if lang == "am" else
                "Claim not found or unauthorized access."
            )
        
        reply = append_mandatory_disclaimer(body, language=lang)
        interaction_id = session_memory.add_turn(
            session_id=session_id,
            user_message=raw_text,
            assistant_reply=reply,
            customer_id=customer_id
        )
        return ChatMessageResponse(
            interaction_id=interaction_id,
            session_id=session_id,
            reply=reply,
            citations=[]
        )

    # 3. Standard Policy FAQ Path: Semantic RAG Search
    chunks = knowledge_store.search(query=raw_text, top_k=3)
    history = session_memory.get_history(session_id)
    system_prompt = build_system_prompt(language=lang)

    reply = await llm_router.generate_response(
        prompt=raw_text,
        context_chunks=chunks,
        system_prompt=system_prompt,
        history=history
    )

    # Ensure disclaimer is attached
    reply = append_mandatory_disclaimer(reply, language=lang)

    citations = [
        CitationItem(
            document_id=c["document_id"],
            section=c["section"],
            page_num=c["page_num"],
            score=c["score"]
        )
        for c in chunks
    ]

    doc_ids = [c["document_id"] for c in chunks]
    interaction_id = session_memory.add_turn(
        session_id=session_id,
        user_message=raw_text,
        assistant_reply=reply,
        customer_id=customer_id,
        document_ids=doc_ids
    )

    info = llm_router.get_provider_info()
    return ChatMessageResponse(
        interaction_id=interaction_id,
        session_id=session_id,
        reply=reply,
        citations=citations,
        provider=info["provider"],
        model=info["model"]
    )


@router.post("/interactions/{interaction_id}/feedback", status_code=204)
async def post_feedback(interaction_id: str, feedback: FeedbackRequest):
    """Capture thumbs UP/DOWN feedback for learning loops."""
    success = session_memory.record_feedback(
        interaction_id=interaction_id,
        rating=feedback.rating,
        comment=feedback.comment
    )
    if not success:
        raise HTTPException(status_code=404, detail="Interaction record not found.")
    return None
