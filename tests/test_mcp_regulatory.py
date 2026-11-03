"""Unit and Integration Tests for Regulatory Registry & MCP Fetcher."""
try:
    import pytest
except ImportError:
    class MockMark:
        def asyncio(self, f): return f
    class MockPytest:
        mark = MockMark()
    pytest = MockPytest()
from app.mcp.registry import regulatory_registry, is_allowed_domain
from app.mcp.server import regulatory_fetcher, sanitize_html, PENDING_APPROVAL_STORE
from app.rag.store import knowledge_store


class TestMcpRegulatory:

    def test_allowlist_domain_validation(self):
        assert is_allowed_domain("https://nbe.gov.et/directives/insurance") is True
        assert is_allowed_domain("https://customs.gov.et/rules") is True
        assert is_allowed_domain("https://localhost:8080/sample") is True
        
        # Unapproved foreign or phishing domains
        assert is_allowed_domain("https://untrusted-hacker.com/malicious") is False
        assert is_allowed_domain("http://phishing-nbe.org.ru/fake") is False

    def test_html_sanitation(self):
        dirty_html = (
            "<html><head><script>alert('injection')</script><style>body{color:red}</style></head>"
            "<body><nav>Home | Login</nav><article><h1>NBE Directive SIB/55</h1>"
            "<p>Insurers must hold 15% liquid solvency ratio.</p></article><footer>Copyright</footer></body></html>"
        )
        clean = sanitize_html(dirty_html)
        assert "<script>" not in clean
        assert "<style>" not in clean
        assert "<nav>" not in clean
        assert "NBE Directive SIB/55" in clean
        assert "Insurers must hold 15% liquid solvency ratio." in clean

    @pytest.mark.asyncio
    async def test_fetch_and_approval_workflow(self):
        # 1. Register valid regulatory URL
        source = regulatory_registry.register_source(
            url="https://nbe.gov.et/insurance-circulars/2026",
            name="NBE Solvency 2026 Circular"
        )
        source_id = source["id"]

        # 2. Trigger fetch
        fetch_res = await regulatory_fetcher.fetch_regulatory_update(
            target_url="https://nbe.gov.et/insurance-circulars/2026",
            source_id=source_id
        )
        assert fetch_res["success"] is True
        assert fetch_res["status"] == "QUEUED_FOR_APPROVAL"
        pending_id = fetch_res["pending_id"]

        # Assert content is NOT yet visible in production vector search
        matches = knowledge_store.search("SIB/55", category="REGULATORY")
        assert len(matches) == 0

        # 3. Compliance officer approves and indexes
        appr_res = regulatory_fetcher.approve_and_index(pending_id=pending_id, reviewer="lead_compliance")
        assert appr_res["status"] == "INDEXED"
        assert appr_res["chunks_indexed"] > 0

        # Assert content IS NOW searchable
        matches_after = knowledge_store.search("SIB/55", category="REGULATORY")
        assert len(matches_after) > 0
