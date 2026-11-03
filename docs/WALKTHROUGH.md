# InsurTech AI Microservice: Comprehensive Implementation Walkthrough

This document details the completed implementation of the **InsurTech AI Microservice** based on `version 1.5 implementation/AI` (`AIA-US-001` through `AIA-US-007`). All 4 execution phases are fully developed, verified locally on your PC, integrated into the frontend applications, and packaged with containerized deployment assets.

---

## 1. Executive Summary & Verification Highlights

- **Service Port**: Configured and bound to **Port 5000** (`HOST=0.0.0.0`, `PORT=5000`).
- **LLM Connectivity**: Flexible multi-provider router supporting **OpenAI**, **Google Gemini**, **Groq**, **local Ollama**, and zero-cost **Mock fallback**. Tested via `scripts/check_llm_connection.py`.
- **Test Results**: **35 / 35 automated tests passing** in `0.22s` (`tests/`) + **7 / 7 interactive module verification suites passing**.
- **Mobile Integration (`insureflow-mobile`)**: React Native customer voice/chat screen (`app/assistant/index.tsx`) with full-duplex WebSocket, Push-to-Talk, barge-in support, citations, and home screen navigation card.
- **Web Admin Integration (`insurance-Web`)**: Angular 18 enterprise backoffice module (`src/app/microservice/ai-assistant/`) featuring 4 functional tabs: Document Ingestion, Q&A Review Desk with Golden-KB promotion, Regulatory Compliance, and PII-scrubbed ShareGPT training export.
- **Production Deployment Assets**: Multi-stage CPU-optimized `Dockerfile`, `docker-compose.vps.yml` with resource limits, Nginx TLS 1.3 reverse proxy configuration with WebSocket upgrade, and automated `vps_smoke_test.sh`.

---

## 2. Phase 1: Local Port 5000 Service & Live Testing

### Key Deliverables:
- **FastAPI Core Application**: [`app/main.py`](file:///home/etech/etech/insurance/insuretech-ai/app/main.py) running on port 5000 with CORS, structured logging, and Prometheus metrics.
- **One-Command Launcher**: [`run_server.sh`](file:///home/etech/etech/insurance/insuretech-ai/run_server.sh) for single-command startup.
- **Live HTTP & WebSocket Test Script**: [`scripts/test_live_api.py`](file:///home/etech/etech/insurance/insuretech-ai/scripts/test_live_api.py) verifying:
  - `GET /healthz` & `GET /readyz`
  - `POST /api/v1/chat/message`
  - `POST /api/v1/kb/search`
  - `POST /api/v1/chat/feedback`
  - `ws://localhost:5000/ws/v1/voice/chat` full-duplex sentence streaming.

```bash
# To launch the local server at any time:
cd insuretech-ai
./run_server.sh

# In another terminal, run live endpoint checks:
.venv/bin/python scripts/test_live_api.py
```

---

## 3. Phase 2: External LLM & Ollama Configuration

### Key Deliverables:
- **Configuration Engine**: [`app/core/config.py`](file:///home/etech/etech/insurance/insuretech-ai/app/core/config.py) loading provider settings from `.env`:
  - `LLM_PROVIDER`: `mock` | `ollama` | `gemini` | `openai` | `groq`
  - `LLM_API_KEY`: External vendor secret key
  - `LLM_BASE_URL`: Base endpoint override
  - `LLM_MODEL`: Provider model identifier (e.g. `llama3.2`, `gpt-4o-mini`, `gemini-1.5-flash`)
- **Connection Diagnostics Tool**: [`scripts/check_llm_connection.py`](file:///home/etech/etech/insurance/insuretech-ai/scripts/check_llm_connection.py) for testing connectivity before launching services.

Sample `.env` setup:
```ini
LLM_PROVIDER=gemini
LLM_API_KEY=AIzaSyYourGeminiApiKeyHere
LLM_MODEL=gemini-1.5-flash
```

---

## 4. Phase 3: Client Applications Integration

### Part A: Mobile App (`insureflow-mobile`)
- [`src/api/aiAssistant.ts`](file:///home/etech/etech/insurance/insureflow-mobile/src/api/aiAssistant.ts): Full-duplex `VoiceChatClient` managing `ws://localhost:5000/ws/v1/voice/chat` with 150ms barge-in `CANCEL_TURN` events.
- [`app/assistant/index.tsx`](file:///home/etech/etech/insurance/insureflow-mobile/app/assistant/index.tsx): Interactive chat UI featuring:
  - Live chat message bubble history with citation chips
  - Mandatory legal disclaimer: `"ይህ መረጃ ለማሳወቂያ ብቻ የቀረበ ነው፤ የመጨረሻ ውሳኔ የሚሰጠው የካሳ ክፍያ ባለሙያው ነው"`
  - Push-to-Talk audio streaming trigger button
  - Quick action suggestion pills in Amharic & English
- [`app/customer/home.tsx`](file:///home/etech/etech/insurance/insureflow-mobile/app/customer/home.tsx): Added AI Assistant card on customer home screen navigating directly to `/assistant`.

### Part B: Web Portal Admin (`insurance-Web`)
- [`src/app/microservice/ai-assistant/ai-assistant.service.ts`](file:///home/etech/etech/insurance/insurance-Web/src/app/microservice/ai-assistant/ai-assistant.service.ts): Angular HTTP client communicating with AI microservice endpoints.
- [`src/app/microservice/ai-assistant/ai-assistant.component.ts`](file:///home/etech/etech/insurance/insurance-Web/src/app/microservice/ai-assistant/ai-assistant.component.ts) & [`.html`](file:///home/etech/etech/insurance/insurance-Web/src/app/microservice/ai-assistant/ai-assistant.component.html):
  1. **Document Ingestion Tab**: Upload policy PDFs, category tagging, asynchronous job tracking, and an interactive Semantic Knowledge Retrieval Sandbox (<80ms response).
  2. **Q&A Review Desk Tab**: Review downvoted user chats (`rating=DOWN`), edit expert responses, and promote verified pairs to the **Golden Knowledge Base** (`GOLDEN_QA`).
  3. **Regulatory Compliance Tab**: Register approved regulatory domains (`*.nbe.gov.et`), run SHA-256 change detection, and approve pending directives into the vector store.
  4. **Training Data Export Tab**: One-click download of PII-sanitized customer interactions in ShareGPT JSONL format.
- [`src/app/app.routes.ts`](file:///home/etech/etech/insurance/insurance-Web/src/app/app.routes.ts): Registered `/services/ai-assistant` protected by employee auth guard.
- [`src/app/pages/service-picker/service-picker.component.ts`](file:///home/etech/etech/insurance/insurance-Web/src/app/pages/service-picker/service-picker.component.ts): Added the "AI Assistant Admin" navigation card on the employee dashboard.

---

## 5. Phase 4: Production Containerization & VPS Assets

All deployment configuration files have been prepared under [`insuretech-ai/`](file:///home/etech/etech/insurance/insuretech-ai/):

| Asset | File | Description |
|---|---|---|
| **Dockerfile** | [`insuretech-ai/Dockerfile`](file:///home/etech/etech/insurance/insuretech-ai/Dockerfile) | Multi-stage build (`python:3.11-slim`), non-root `appuser` (UID 10001), `ffmpeg`, `libgomp1`, and Amharic OCR packages. |
| **Docker Compose** | [`insuretech-ai/docker-compose.vps.yml`](file:///home/etech/etech/insurance/insuretech-ai/docker-compose.vps.yml) | Orchestrates `ai-assistant` (port 5000), `pgvector` (5432), `redis` (6379), `ollama` (11434), and `nginx` (80/443) with CPU/memory resource limits. |
| **Nginx Reverse Proxy** | [`insuretech-ai/nginx/nginx.conf`](file:///home/etech/etech/insurance/insuretech-ai/nginx/nginx.conf) | Token-bucket rate limiting (15 req/s), WebSocket connection upgrade for voice, and 25MB body upload limits. |
| **Smoke Test Suite** | [`insuretech-ai/scripts/vps_smoke_test.sh`](file:///home/etech/etech/insurance/insuretech-ai/scripts/vps_smoke_test.sh) | Automated post-deploy verification probe suite checking liveness, readiness, PII gate, metrics, and RAG. |

---

## 6. How to Deploy to VPS (When Ready)

When you are ready to deploy to your Linux VPS:

```bash
# 1. Copy the microservice directory to your VPS:
rsync -avz insuretech-ai/ user@your-vps-ip:/opt/insurtech-ai/

# 2. Configure production secrets in .env on the VPS:
cd /opt/insurtech-ai
cp .env.example .env
nano .env

# 3. Start the entire container stack in background:
docker compose -f docker-compose.vps.yml up -d --build

# 4. Verify deployment health with the automated smoke test:
./scripts/vps_smoke_test.sh http://localhost:5000
```
