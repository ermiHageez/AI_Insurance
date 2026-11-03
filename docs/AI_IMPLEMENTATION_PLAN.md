# InsurTech AI Assistant (AIA) Microservice: Local Implementation & Testing Plan

## Goal Description
Implement and thoroughly verify all AI modules and functionality for the InsurTech AI Assistant (`insuretech-ai`) directly on the **local development machine**. 

The implementation will build the full microservice architecture (FastAPI running on **Port 5000**, Ge'ez Normalizer, RAG Pipeline with table extraction, Grounded Conversational Core with IDOR-protected claims tool, MCP Regulatory Scraper, Voice Pipeline with barge-in, Admin Review Desk, and PII-safe JSONL exporter). 

It is tailored for **local PC testing**: supporting both local Ollama and external LLM APIs (via API key), standalone mock/fallback modes for offline CPU testing, comprehensive automated pytest suites, and an interactive local CLI/HTTP test runner so all functionality can be validated end-to-end without needing remote deployment.

```
                                      +------------------------------------+
                                      |    Local Client / Test Runners     |
                                      |  (pytest, CLI runner, Web / Mobile)|
                                      +-----------------+------------------+
                                                        | (Port 5000)
                                                        v
                                      +-----------------+------------------+
                                      |   FastAPI Service (insuretech-ai)  |
                                      +----+-----------+----------+----+---+
                                           |           |          |    |
           +-------------------------------+           |          |    +------------------------------+
           v                                           v          v                                   v
+--------------------+                       +------------+  +---------+                    +--------------------+
| Ge'ez Normalizer & |                       | MCP Client |  |  Redis  |                    | Voice Pipeline     |
| RAG Engine         |                       | & Claims   |  | Memory  |                    | faster-whisper     |
| (pgvector / bge-m3)|                       | IDOR Tool  |  | & Cache |                    | & OmniVoice TTS    |
+--------------------+                       +------------+  +---------+                    +--------------------+
                                                   |
                                                   v
                                     +---------------------------+
                                     | LLM Provider Router       |
                                     | - Local Ollama            |
                                     | - External API + API KEY  |
                                     | - Mock Provider (Testing) |
                                     +---------------------------+
```

---

## User Review Required

> [!IMPORTANT]
> **Service Port Configuration:**
> The AI microservice will run on **Port 5000** (e.g. `http://localhost:5000`) for both local uvicorn processes and local containerized configurations, avoiding any conflicts with port 8000.

> [!IMPORTANT]
> **Flexible LLM Provider (Ollama or API Key):**
> The service supports three LLM execution modes configured via `.env`:
> 1. `ollama`: Uses local Ollama instance (`http://localhost:11434` or `http://ollama:11434`).
> 2. `api_key`: Uses external cloud LLM (OpenAI, Gemini, Groq, or Ollama Cloud) via `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
> 3. `mock`: High-fidelity deterministic mock LLM provider for instant offline local testing without requiring active models or API keys.

> [!WARNING]
> **Mandatory Legal Disclaimer:**
> In both local tests and production replies, every policy-related answer unconditionally includes the official Amharic disclaimer:
> `"ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"`

---

## Open Questions

> [!NOTE]
> 1. **Local Backing Stores**: Would you prefer running PostgreSQL (with pgvector) and Redis via a lightweight local Docker command (`docker compose -f docker-compose.local.yml up -d`), or having an in-memory/SQLite vector fallback for zero-dependency test execution? *(Plan default: We will support both! Local Docker Compose provides real pgvector/Redis on port 5432/6379, while unit tests can also run with in-memory adapters for instant test suite execution)*.
> 2. **External LLM Model Choice**: If using an API Key, which cloud provider do you plan to use (OpenAI `gpt-4o-mini`, Google Gemini `gemini-1.5-flash`, Groq `llama-3.3-70b`, etc.)? The unified client is OpenAI-compatible so it works seamlessly across all major providers.

---

## Proposed Changes

### Component 1: `insuretech-ai` Foundation & Local Configuration (AIA-US-001)

Setup the Python microservice structure on Port 5000 with environment configuration supporting local Ollama and external API keys.

#### [NEW] `insuretech-ai/pyproject.toml` & `requirements.txt`
- Python 3.11+ dependencies: `fastapi`, `uvicorn[standard]`, `structlog`, `prometheus-client`, `pydantic`, `pydantic-settings`, `asyncpg`, `pgvector`, `redis`, `httpx`, `pymupdf`, `pytesseract`, `mcp`, `python-jose`, `numpy`, `pytest`, `pytest-asyncio`.

#### [NEW] `insuretech-ai/.env.example` & `.env`
- Configuration defaults:
  - `PORT=5000`
  - `LLM_PROVIDER=ollama` (options: `ollama`, `openai_compatible`, `mock`)
  - `LLM_API_KEY=""` (optional: user API key for Gemini / OpenAI / Groq)
  - `LLM_BASE_URL="http://localhost:11434/v1"`
  - `LLM_MODEL="qwen2.5:3b"`
  - `DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/insuretech_ai"`
  - `REDIS_URL="redis://localhost:6379/0"`
  - `JWT_SECRET_KEY="local-dev-secret-key-change-in-prod"`

#### [NEW] `insuretech-ai/docker-compose.local.yml`
- Minimal local backing services:
  - `pgvector`: PostgreSQL 16 with pgvector on port 5432
  - `redis`: Redis 7 on port 6379
  - Optional `fastapi-app`: mapped to host port **5000:5000**

#### [NEW] `insuretech-ai/app/core/config.py`
- Pydantic Settings supporting Port 5000, `LLM_API_KEY`, `LLM_PROVIDER`, database & redis credentials, and rate limits.

#### [NEW] `insuretech-ai/app/main.py`
- FastAPI app factory with CORS, structlog logging, Prometheus metrics, and lifecycle handlers.

#### [NEW] `insuretech-ai/app/api/v1/health.py`
- `GET /healthz` $\to$ `{"status": "ok", "port": 5000}`
- `GET /readyz` $\to$ Checks status of LLM provider (Ollama or API), pgvector, and Redis.

---

### Component 2: Ge'ez Normalizer & Policy Document RAG Pipeline (AIA-US-002)

Build the Amharic text normalizer and document chunking/search pipeline.

#### [NEW] `insuretech-ai/app/rag/normalizer.py`
- Pure-function Amharic/Ge'ez normalizer:
  - Homophone folding:
    - ሐ/ኀ/ኃ/ኋ/ሗ/ኅ/ኁ $\to$ ሀ-family
    - ሠ/ሡ/ሢ/ሣ/ሤ/ሥ/ሦ $\to$ ሰ-family
    - ዐ/ዑ/ዒ/ዓ/ዔ/ዕ/ዖ $\to$ አ-family
    - ፀ/ፁ/ፂ/ፃ/ፄ/ፅ/ፆ $\to$ ጸ-family
  - Ethiopic punctuation standardization (`፡` $\to$ space, `፣` $\to$ `,`, `።` $\to$ `.`).
  - Idempotent and executes in < 5ms for 1,000 words.

#### [NEW] `insuretech-ai/app/rag/extractor.py`
- PyMuPDF text and tabular extraction with fallback OCR. Preserves deductible tables and structure.

#### [NEW] `insuretech-ai/app/rag/chunker.py`
- Semantic chunker: 512-token target with 10% overlap, respecting policy headings and table boundaries.

#### [NEW] `insuretech-ai/app/rag/embedder.py`
- Embedder interface with dual implementation:
  - Real embedding using `BAAI/bge-m3` or fast local ONNX/sentence-transformers.
  - In-memory deterministic mock embedder for rapid local unit testing without downloading 2GB models.

#### [NEW] `insuretech-ai/app/rag/store.py`
- Vector store with pgvector table (`knowledge_chunks`) and an in-memory cosine fallback for standalone local tests. Top-5 citation search in < 80ms.

#### [NEW] `insuretech-ai/app/api/v1/kb.py`
- `POST /api/v1/kb/documents/upload`: Multipart upload with validation.
- `GET /api/v1/kb/documents/jobs/{jobId}`: Job extraction status and report.
- `POST /api/v1/kb/search`: Semantic query endpoint with Ge'ez query normalization.

---

### Component 3: LLM Provider Router & Grounded Conversational Core (AIA-US-003)

Unified LLM routing (local Ollama or external API key) with prompt guardrails, IDOR protection, and PII scrubbing.

#### [NEW] `insuretech-ai/app/llm/router.py`
- Unified async LLM client supporting:
  - Local Ollama via HTTP API
  - External API with `LLM_API_KEY` (Gemini, OpenAI, Groq) via standard OpenAI-compatible protocol
  - Mock Provider generating realistic grounded responses for local test suites

#### [NEW] `insuretech-ai/app/core/guardrails.py`
- Grounding prompts, zero-shot injection defense, no-context refusal, and mandatory disclaimer:
  `"ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"`

#### [NEW] `insuretech-ai/app/tools/claims.py`
- MCP Claim Status Tool:
  - Extracts caller `customer_id` strictly from Keycloak JWT `sub`.
  - IDOR Defense: Verifies `claim.customerId == token.sub`.
  - On mismatch: Returns generic `"Claim not found or unauthorized access"` and records security event.

#### [NEW] `insuretech-ai/app/core/pii_scrubber.py`
- Redacts Ethiopian phone numbers (`+251...`, `09...`, `07...`), TINs, Kebele IDs, and Bank Accounts.

#### [NEW] `insuretech-ai/app/core/session_memory.py`
- Redis-backed conversation memory with 30-minute rolling TTL and local in-memory fallback.

#### [NEW] `insuretech-ai/app/api/v1/chat.py`
- `POST /api/v1/chat/messages`: Grounded chat endpoint on Port 5000.
- `POST /api/v1/chat/interactions/{id}/feedback`: Thumbs UP / DOWN feedback.

---

### Component 4: Regulatory Source Registry & MCP Fetcher (AIA-US-004)

Admin registry and change detection for Ethiopian regulatory rules.

#### [NEW] `insuretech-ai/app/mcp/registry.py` & `server.py`
- Whitelisted domain verification (e.g. NBE portals).
- Scraper stripping scripts, CSS, and navigation.
- SHA-256 change detection storing diffs in `pending_approval`.

#### [NEW] `insuretech-ai/app/api/v1/admin_sources.py`
- Source registration, pending queue, and "Approve and Index" endpoint.

---

### Component 5: Real-Time Amharic Voice Pipeline (AIA-US-005)

Voice processing modules, sentence accumulator, and WebSocket server.

#### [NEW] `insuretech-ai/app/voice/stt.py` & `tts.py`
- `faster-whisper` STT and `OmniVoice` TTS adapters with fast local mock/CPU fallback modes.

#### [NEW] `insuretech-ai/app/voice/sentence_accumulator.py`
- Splits streamed LLM tokens on Ethiopic punctuation (`።`, `፣`) and Latin punctuation to stream early audio sentences.

#### [NEW] `insuretech-ai/app/voice/audio_cache.py`
- Redis-backed TTS audio cache (SHA-256 of text, 7-day TTL).

#### [NEW] `insuretech-ai/app/api/v1/voice_socket.py`
- WebSocket endpoint `/ws/v1/voice/chat`:
  - Push-to-talk audio streaming.
  - 150ms Barge-In interruption via `CANCEL_TURN`.

---

### Component 6: Admin Review Loop & Training Export (AIA-US-007)

Golden KB promotion and defense-in-depth PII export gate.

#### [NEW] `insuretech-ai/app/api/v1/admin_review.py`
- Review desk for downvoted answers (`GET /api/v1/admin/review/interactions`).
- Golden-KB promotion (`POST /api/v1/admin/review/interactions/{id}/promote`).
- Training export (`GET /api/v1/admin/export/training-data`) with strict multi-pattern PII validator refusing download (422) if raw PII exists.

---

### Component 7: Local Test Harness & CLI Verification Script

Tools to let you test every module directly on your local machine.

#### [NEW] `insuretech-ai/scripts/verify_local.py`
- Interactive local CLI tool to test:
  1. Ge'ez Normalization across sample homophone pairs.
  2. Document ingestion and chunk retrieval.
  3. LLM generation (using local Ollama, configured API Key, or Mock).
  4. IDOR claim security with matching and mismatched tokens.
  5. Voice synthesis and barge-in cancellation test.
  6. PII scrubber and training data export.

#### [NEW] `insuretech-ai/tests/` (Automated Pytest Suite)
- `test_normalizer.py`: 50+ Amharic homophone and punctuation test cases.
- `test_pii_scrubber.py`: Ethiopian phone numbers, Kebele IDs, TINs, Bank Accounts.
- `test_claim_idor.py`: Verifies JWT owner match vs cross-customer probe block.
- `test_llm_guardrails.py`: Tests prompt injection defense and mandatory disclaimer.
- `test_rag_pipeline.py`: Ingestion, chunking, and citation search tests.
- `test_voice_barge_in.py`: WebSocket voice stream and 150ms barge-in test.
- `test_export_pii_gate.py`: Validates ShareGPT JSONL export and 422 PII block.

---

## Verification Plan

### Automated Tests (Local PC)
Run from the `insuretech-ai` directory:
```bash
# Run the complete test suite locally
pytest -v tests/
```
Coverage checkpoints:
- `test_normalizer.py`: 100% pass on all Ge'ez character foldings.
- `test_pii_scrubber.py`: All Ethiopian phone/ID/TIN patterns redacted.
- `test_claim_idor.py`: Unauthorized claim probe returns 404/unauthorized, security event logged.
- `test_llm_guardrails.py`: Injection blocked, disclaimer present in all answers.
- `test_voice_barge_in.py`: `CANCEL_TURN` halts worker within 150ms.
- `test_export_pii_gate.py`: Seeded PII payload rejected with HTTP 422.

### Manual Local Verification
1. **Start the local service on Port 5000**:
   ```bash
   cd insuretech-ai
   python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
   ```
2. **Verify Health and Port**:
   ```bash
   curl http://localhost:5000/healthz
   # Expect: {"status": "ok", "port": 5000}
   ```
3. **Run the Interactive Local Verification Script**:
   ```bash
   python scripts/verify_local.py
   ```
   This script runs an end-to-end interactive simulation testing Amharic Q&A, claim lookup, voice streaming, and PII scrubbing directly on your terminal.
