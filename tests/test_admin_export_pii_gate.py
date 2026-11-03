"""Integration Tests for Golden-KB Promotion & Defense-in-Depth PII Export Gate."""
import json
try:
    import pytest
except ImportError:
    pytest = None
from app.core.session_memory import session_memory, CHAT_INTERACTIONS_STORE
from app.api.v1.admin_review import promote_to_golden_kb, export_training_data, PromoteRequest, HTTPException
from app.rag.store import knowledge_store


@pytest.mark.asyncio
class TestAdminExportPiiGate:

    def setup_method(self):
        CHAT_INTERACTIONS_STORE.clear()
        knowledge_store.clear()

    async def test_golden_kb_promotion(self):
        # 1. Simulate a downvoted interaction
        int_id = session_memory.add_turn(
            session_id="session-test-01",
            user_message="What is the coverage limit for third-party injury?",
            assistant_reply="The coverage limit is not clearly stated.",
            customer_id="cust-101"
        )
        session_memory.record_feedback(int_id, rating="DOWN", comment="Inaccurate answer")

        # 2. Insurance expert promotes corrected answer
        req = PromoteRequest(
            corrected_answer="The mandatory Third Party bodily injury liability limit is 500,000 ETB per victim under Proclamation 799/2013.",
            reviewer="expert_claims_officer"
        )
        res = await promote_to_golden_kb(interaction_id=int_id, request=req)

        assert res["status"] == "PROMOTED_TO_GOLDEN_KB"
        assert res["chunks_indexed"] > 0

        # 3. Verify retrieval now surfaces the golden answer
        matches = knowledge_store.search("coverage limit for third-party injury", category="GOLDEN_QA")
        assert len(matches) > 0
        assert "500,000 ETB" in matches[0]["content_text"]

    async def test_export_clean_payload_succeeds(self):
        session_memory.add_turn(
            session_id="session-clean",
            user_message="How do I renewal my motor policy?",
            assistant_reply="You can renew online via the mobile app payment gateway.",
            customer_id="cust-102"
        )

        response = await export_training_data()
        assert response.status_code == 200
        content_lines = response.body.decode('utf-8').strip().split('\n')
        assert len(content_lines) >= 1
        data = json.loads(content_lines[0])
        assert "conversations" in data

    async def test_export_blocked_with_422_when_pii_detected(self):
        # Deliberately seed an unscrubbed PII interaction into raw store
        raw_phone = "+251911998877"
        CHAT_INTERACTIONS_STORE["bad-interaction"] = {
            "id": "bad-interaction",
            "session_id": "session-dirty",
            "customer_id": "cust-leak",
            "scrubbed_prompt": f"Please call me at raw phone {raw_phone}",
            "scrubbed_response": "We will reach out.",
            "model": "qwen2.5:3b",
            "document_ids": [],
            "rating": None,
            "created_at": 1000.0
        }

        # Attempt to export -> PII validator must intercept and return HTTP 422
        with pytest.raises(HTTPException) as exc_info:
            await export_training_data()

        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["error"] == "PII_VALIDATION_FAILED"
        assert "PHONE" in detail["detected_categories"]
