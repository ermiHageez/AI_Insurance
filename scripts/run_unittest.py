#!/usr/bin/env python3
"""Standalone Unit & Integration Test Runner using Python's built-in unittest.

Executes all 8 test suites without requiring any external test runners:
1. Ge'ez Homophone & Punctuation Normalizer
2. Ethiopian PII Scrubber & Validator Gate
3. Claim Status IDOR Ownership Defense
4. LLM Guardrails & Mandatory Disclaimer
5. RAG Document Ingestion & Homophone Retrieval
6. Regulatory Registry & MCP Change Detector
7. Voice Pipeline, Sentence Accumulator & Barge-In
8. Admin Golden-KB Promotion & Defense-in-Depth PII Gate
"""
import sys
import os
import unittest
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_normalizer import TestGeezNormalizer
from tests.test_pii_scrubber import TestPiiScrubber
from tests.test_claim_idor import TestClaimIdorSecurity
from tests.test_llm_guardrails import TestLlmGuardrails
from tests.test_rag_pipeline import TestRagPipeline
from tests.test_mcp_regulatory import TestMcpRegulatory
from tests.test_voice_barge_in import TestVoiceBargeInPipeline
from tests.test_admin_export_pii_gate import TestAdminExportPiiGate


def make_async_test(coro_fn):
    """Helper to adapt async test functions to standard unittest TestCase."""
    def wrapper(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_fn(self))
        finally:
            loop.close()
    return wrapper


class AsyncTestCaseAdapter(unittest.TestCase):
    """Adapter running async methods under standard unittest."""
    pass


def load_test_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    # Normalizer Tests
    class NormalizerTests(unittest.TestCase):
        def setUp(self): self.t = TestGeezNormalizer()
        def test_homophone_ha_family(self): self.t.test_homophone_ha_family()
        def test_homophone_sa_family(self): self.t.test_homophone_sa_family()
        def test_homophone_a_family(self): self.t.test_homophone_a_family()
        def test_homophone_tsa_family(self): self.t.test_homophone_tsa_family()
        def test_ethiopic_punctuation_standardization(self): self.t.test_ethiopic_punctuation_standardization()
        def test_idempotency_property(self): self.t.test_idempotency_property()
        def test_performance_under_5ms(self): self.t.test_performance_under_5ms()
        def test_mixed_english_amharic_integrity(self): self.t.test_mixed_english_amharic_integrity()
    suite.addTests(loader.loadTestsFromTestCase(NormalizerTests))

    # PII Scrubber Tests
    class PiiScrubberTests(unittest.TestCase):
        def setUp(self): self.t = TestPiiScrubber()
        def test_scrub_ethiopian_phone_formats(self): self.t.test_scrub_ethiopian_phone_formats()
        def test_scrub_bank_accounts(self): self.t.test_scrub_bank_accounts()
        def test_scrub_kebele_id(self): self.t.test_scrub_kebele_id()
        def test_no_false_positive_on_policy_text(self): self.t.test_no_false_positive_on_policy_text()
        def test_contains_pii_validator_gate(self): self.t.test_contains_pii_validator_gate()
    suite.addTests(loader.loadTestsFromTestCase(PiiScrubberTests))

    # IDOR Security Tests
    class IdorSecurityTests(unittest.TestCase):
        def setUp(self): self.t = TestClaimIdorSecurity()
        def test_authorized_owner_access(self):
            asyncio.run(self.t.test_authorized_owner_access())
        def test_cross_customer_probe_blocked(self):
            asyncio.run(self.t.test_cross_customer_probe_blocked())
        def test_nonexistent_claim_returns_same_generic_error(self):
            asyncio.run(self.t.test_nonexistent_claim_returns_same_generic_error())
    suite.addTests(loader.loadTestsFromTestCase(IdorSecurityTests))

    # LLM Guardrails Tests
    class LlmGuardrailsTests(unittest.TestCase):
        def setUp(self): self.t = TestLlmGuardrails()
        def test_injection_pattern_detection(self): self.t.test_injection_pattern_detection()
        def test_mandatory_disclaimer_appended(self): self.t.test_mandatory_disclaimer_appended()
        def test_no_context_refusal(self):
            asyncio.run(self.t.test_no_context_refusal())
        def test_injection_blocked_in_llm_generation(self):
            asyncio.run(self.t.test_injection_blocked_in_llm_generation())
    suite.addTests(loader.loadTestsFromTestCase(LlmGuardrailsTests))

    # RAG Pipeline Tests
    class RagPipelineTests(unittest.TestCase):
        def setUp(self):
            self.t = TestRagPipeline()
            self.t.setup_method()
        def test_semantic_chunker_table_preservation(self): self.t.test_semantic_chunker_table_preservation()
        def test_rag_homophone_folding_retrieval(self): self.t.test_rag_homophone_folding_retrieval()
        def test_idempotent_reupload(self): self.t.test_idempotent_reupload()
    suite.addTests(loader.loadTestsFromTestCase(RagPipelineTests))

    # MCP Regulatory Tests
    class McpRegulatoryTests(unittest.TestCase):
        def setUp(self): self.t = TestMcpRegulatory()
        def test_allowlist_domain_validation(self): self.t.test_allowlist_domain_validation()
        def test_html_sanitation(self): self.t.test_html_sanitation()
        def test_fetch_and_approval_workflow(self):
            asyncio.run(self.t.test_fetch_and_approval_workflow())
    suite.addTests(loader.loadTestsFromTestCase(McpRegulatoryTests))

    # Voice Barge-In Tests
    class VoiceBargeInTests(unittest.TestCase):
        def setUp(self): self.t = TestVoiceBargeInPipeline()
        def test_sentence_accumulator_punctuation_splitting(self): self.t.test_sentence_accumulator_punctuation_splitting()
        def test_audio_cache_latency_under_100ms(self):
            asyncio.run(self.t.test_audio_cache_latency_under_100ms())
        def test_barge_in_cancellation_latency_under_150ms(self):
            asyncio.run(self.t.test_barge_in_cancellation_latency_under_150ms())
    suite.addTests(loader.loadTestsFromTestCase(VoiceBargeInTests))

    # Admin Export PII Gate Tests
    class AdminExportTests(unittest.TestCase):
        def setUp(self):
            self.t = TestAdminExportPiiGate()
            self.t.setup_method()
        def test_golden_kb_promotion(self):
            asyncio.run(self.t.test_golden_kb_promotion())
        def test_export_clean_payload_succeeds(self):
            asyncio.run(self.t.test_export_clean_payload_succeeds())
        def test_export_blocked_with_422_when_pii_detected(self):
            asyncio.run(self.t.test_export_blocked_with_422_when_pii_detected())
    suite.addTests(loader.loadTestsFromTestCase(AdminExportTests))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = load_test_suite()
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
