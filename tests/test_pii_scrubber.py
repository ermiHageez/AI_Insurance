"""Unit Tests for Ethiopian PII Scrubber & Validator Gate."""
from app.core.pii_scrubber import scrub_pii, contains_pii


class TestPiiScrubber:

    def test_scrub_ethiopian_phone_formats(self):
        # +251 9... format
        p1 = "My phone number is +251 911 234567 please call me."
        assert scrub_pii(p1) == "My phone number is [REDACTED_PHONE] please call me."

        # +2517... Safaricom Ethiopia format
        p2 = "Reach me at +251712345678 immediately."
        assert "[REDACTED_PHONE]" in scrub_pii(p2)
        assert "+251712345678" not in scrub_pii(p2)

        # 09... standard domestic format
        p3 = "ስልክ ቁጥሬ 0911223344 ነው"
        assert scrub_pii(p3) == "ስልክ ቁጥሬ [REDACTED_PHONE] ነው"

        # 07... domestic format
        p4 = "ስልክ: 0722334455"
        assert "[REDACTED_PHONE]" in scrub_pii(p4)

    def test_scrub_bank_accounts(self):
        acc = "Please transfer the claim payout to CBE Account: 1000123456789"
        scrubbed = scrub_pii(acc)
        assert "[REDACTED_ACCOUNT]" in scrubbed
        assert "1000123456789" not in scrubbed

    def test_scrub_kebele_id(self):
        id_text = "የቀበሌ መታወቂያዬ Kebele: AA-04-123456 ነው"
        scrubbed = scrub_pii(id_text)
        assert "[REDACTED_ID]" in scrubbed
        assert "AA-04-123456" not in scrubbed

    def test_no_false_positive_on_policy_text(self):
        # Ensure policy amounts, sections, and dates are not incorrectly redacted
        policy_clause = (
            "Section 4.2: Maximum Third Party Liability coverage is 500,000 ETB. "
            "Deductible applies at 2.5% or minimum 5,000 ETB per incident on 2026-10-15."
        )
        scrubbed = scrub_pii(policy_clause)
        assert "500,000 ETB" in scrubbed
        assert "5,000 ETB" in scrubbed
        assert "Section 4.2" in scrubbed

    def test_contains_pii_validator_gate(self):
        clean_text = "What is the deductible for commercial vehicle third party insurance?"
        has_pii, categories = contains_pii(clean_text)
        assert not has_pii
        assert categories == []

        dirty_text = "Customer phone +251911002233 asking for settlement."
        has_pii, categories = contains_pii(dirty_text)
        assert has_pii
        assert "PHONE" in categories
