# InsurTech AI Assistant: Testing Guide & Reference

## 10-Line Quick Start

```bash
cd insuretech-ai
# 1. Start the isolated test containers
make up
# 2. Seed Ethiopian policy PDF, Golden QA, and regulatory source
make seed
# 3. Mint a valid JWT for testing
make token USER=customerA
# 4. Run unit and integration tests
make test
# 5. Run security gate test suite (known gaps xfail)
make test-security
# 6. Execute full automated smoke test
make smoke
# 7. Tear down test containers
make down
```

---

## Pytest Test Markers

* **`pytest -m "unit"`**: Fast, offline unit tests (normalizer, PII scrubber, guardrails).
* **`pytest -m "integration"`**: RAG pipeline, Golden KB promotion, WebSocket barge-in.
* **`pytest -m "security"`**: Authentication checks, IDOR claim lookup, prompt injection.
* **`pytest -m "live"`**: Real external API calls (e.g. Gemini cloud inference; skipped by default).

To run all non-live tests:
```bash
pytest -m "not live"
```

---

## Ready-to-Use HTTP Request Collection

A ready-to-use REST client collection is provided in [`tests/test_requests.http`](tests/test_requests.http).
Supported in VS Code REST Client, IntelliJ HTTP Client, and Bruno.

### Sample Minted Tokens

* **customerA**:
  ```bash
  python3 scripts/dev_token_issuer.py customerA valid
  ```
* **customerB**:
  ```bash
  python3 scripts/dev_token_issuer.py customerB valid
  ```
* **admin**:
  ```bash
  python3 scripts/dev_token_issuer.py admin valid
  ```
* **Security Variants**:
  * `python3 scripts/dev_token_issuer.py customerA expired`
  * `python3 scripts/dev_token_issuer.py customerA wrong_signature`
  * `python3 scripts/dev_token_issuer.py customerA alg_none`
