"""Session Memory & Interaction Store with PII Redaction.

Manages multi-turn chat sessions with rolling 30-minute TTL,
records append-only scrubbed interactions, and captures thumbs UP/DOWN feedback.
"""
import time
import uuid
from typing import List, Dict, Any, Optional
from app.core.pii_scrubber import scrub_pii

# Append-only interaction store
# id -> {id, sessionId, customerId, scrubbedPrompt, scrubbedResponse, model, documentIds, rating, timestamp}
CHAT_INTERACTIONS_STORE: Dict[str, Dict[str, Any]] = {}


class SessionMemoryManager:
    """Manages active conversation sessions with rolling TTL and bounded turn window."""

    def __init__(self, ttl_seconds: int = 1800, max_turns: int = 6):
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        # session_id -> {"last_active": timestamp, "turns": [{"role": "user"|"assistant", "content": str}]}
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve conversation history if session is active within TTL."""
        if not session_id or session_id not in self._sessions:
            return []

        session = self._sessions[session_id]
        now = time.time()
        
        # Check TTL expiry
        if now - session["last_active"] > self.ttl_seconds:
            self._sessions.pop(session_id, None)
            return []

        return session["turns"]

    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        customer_id: str = "anonymous",
        document_ids: Optional[List[str]] = None,
        model: str = "qwen2.5:3b"
    ) -> str:
        """Add user/assistant turn, scrub PII, refresh TTL, and record interaction.
        
        Returns:
            interaction_id for feedback linking.
        """
        now = time.time()
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "customer_id": customer_id,
                "last_active": now,
                "turns": []
            }

        session = self._sessions[session_id]
        session["last_active"] = now

        # Add turns to sliding context window
        session["turns"].append({"role": "user", "content": user_message})
        session["turns"].append({"role": "assistant", "content": assistant_reply})

        # Bound turn window to prevent context overflow
        if len(session["turns"]) > self.max_turns * 2:
            session["turns"] = session["turns"][-self.max_turns * 2:]

        # PII Scrubbing prior to persistent logging
        scrubbed_user = scrub_pii(user_message)
        scrubbed_reply = scrub_pii(assistant_reply)

        interaction_id = str(uuid.uuid4())
        CHAT_INTERACTIONS_STORE[interaction_id] = {
            "id": interaction_id,
            "session_id": session_id,
            "customer_id": customer_id,
            "scrubbed_prompt": scrubbed_user,
            "scrubbed_response": scrubbed_reply,
            "model": model,
            "document_ids": document_ids or [],
            "rating": None,
            "feedback_comment": None,
            "created_at": now
        }

        return interaction_id

    def record_feedback(self, interaction_id: str, rating: str, comment: Optional[str] = None) -> bool:
        """Link thumbs UP / DOWN feedback to an interaction record."""
        if interaction_id not in CHAT_INTERACTIONS_STORE:
            return False

        record = CHAT_INTERACTIONS_STORE[interaction_id]
        record["rating"] = rating.upper()  # UP or DOWN
        record["feedback_comment"] = comment
        return True

    def clear(self):
        """Reset session memory."""
        self._sessions.clear()


session_memory = SessionMemoryManager()
