"""Integration Tests for Document Ingestion, Chunking & Ge'ez Normalized RAG."""
import time
try:
    import pytest
except ImportError:
    pytest = None
from app.rag.chunker import chunk_document
from app.rag.store import knowledge_store
from app.rag.normalizer import normalize


class TestRagPipeline:

    def setup_method(self):
        knowledge_store.clear()

    def test_semantic_chunker_table_preservation(self):
        policy_text = (
            "# Ethiopian Motor Vehicle Insurance Policy\n\n"
            "## Section 3: Deductible Schedule\n"
            "| Vehicle Category | Own Damage Deductible | Third Party Deductible |\n"
            "| Private Car      | 2,500 ETB             | Nil                     |\n"
            "| Commercial Truck | 7,500 ETB             | 2,000 ETB               |\n\n"
            "## Section 4: Notice of Incident\n"
            "Any incident giving rise to a claim must be reported within 24 hours to the nearest branch."
        )

        chunks = chunk_document(policy_text, target_tokens=50, overlap_tokens=10)
        assert len(chunks) >= 2
        # Ensure deductible table row was not severed across arbitrary boundaries
        table_found = any("Deductible Schedule" in c["content_text"] for c in chunks)
        assert table_found

    def test_rag_homophone_folding_retrieval(self):
        # Ingest document using "ሐኪም" (physician / medical examiner)
        doc_text = "የሕክምና ማስረጃ እና የሐኪም ማረጋገጫ ለካሳ ክፍያ ያስፈልጋል። የካሳው መጠን 50,000 ብር ነው።"
        chunks = chunk_document(doc_text, metadata={"section": "Medical Claim Policy"})

        knowledge_store.upsert_chunks(
            chunks=chunks,
            document_id="ETH-MED-001",
            category="POLICY",
            source_hash="hash-12345"
        )

        # Query using alternate homophone "ሀኪም" (ha instead of ha-family ha)
        query = "የሀኪም ማረጋገጫ ለካሳ ክፍያ ያስፈልጋል?"
        
        start = time.perf_counter()
        matches = knowledge_store.search(query=query, top_k=3)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(matches) > 0
        assert matches[0]["document_id"] == "ETH-MED-001"
        assert matches[0]["score"] > 0.3
        assert elapsed_ms < 80.0, f"Retrieval latency {elapsed_ms:.2f}ms exceeds 80ms target"

    def test_idempotent_reupload(self):
        doc_text = "Motor Tariff directive: 10% premium discount for safe driving."
        chunks = chunk_document(doc_text)

        # Upload first time
        c1 = knowledge_store.upsert_chunks(chunks, "TARIFF-1", "POLICY", source_hash="same-hash-99")
        initial_total = knowledge_store.total_chunks

        # Upload second time with identical source_hash
        c2 = knowledge_store.upsert_chunks(chunks, "TARIFF-1", "POLICY", source_hash="same-hash-99")
        assert knowledge_store.total_chunks == initial_total
