# InsurTech AI Microservice

> **Ethiopian InsurTech AI Microservice**: Multilingual Amharic/English RAG, Whisper Voice Streaming, PII Redaction, Regulatory Directive Sync & Golden Knowledge Base.
> Operating Port: **5000** | Python 3.11+ / FastAPI

---

## 📚 Complete Project Documentation

All plans, architecture specifications, step-by-step records, and verification walkthroughs are documented in the [`docs/`](docs/) directory:

1. [**AI Implementation Plan**](docs/AI_IMPLEMENTATION_PLAN.md): Full blueprint for `AIA-US-001` through `AIA-US-007`, security constraints, Ethiopian PII rules, and RAG design.
2. [**AI Microservice Architecture**](docs/AI_MICROSERVICE_ARCHITECTURE.md): Network topology, component diagram, sequence flows, IDOR defense matrix, Ge'ez homophone tables, and voice latency budgets.
3. [**Step-by-Step Execution Plan**](docs/STEP_BY_STEP_EXECUTION_PLAN.md): The 4 sequential phases executed from local Port 5000 verification up to production VPS containerization.
4. [**Walkthrough & Verification Guide**](docs/WALKTHROUGH.md): 35/35 automated pytest test results, live endpoint tests, mobile & web frontend integrations, and VPS deployment commands.

---

## ⚡ Quick Start (Local PC)

### 1. Launch the Server on Port 5000
```bash
./run_server.sh
```

### 2. Run All Automated & Interactive Verification Tests
```bash
./test.sh
```

### 3. Verify Live HTTP & WebSocket Voice Stream
```bash
.venv/bin/python3 scripts/test_live_api.py
```

### 4. Test External LLM Provider or Local Ollama
```bash
.venv/bin/python3 scripts/check_llm_connection.py
```

---

## 🌐 Key API Endpoints (Port 5000)

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | GET | Liveness probe: returns `{"status":"ok","port":5000}` |
| `/readyz` | GET | Readiness probe: checks database, redis, and active LLM provider |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/v1/chat/message` | POST | Grounded chat with Amharic disclaimer & citation chips |
| `/api/v1/chat/feedback` | POST | User feedback (UP/DOWN rating) on chat responses |
| `/api/v1/kb/documents/upload` | POST | Async policy/tariff document upload & semantic chunking |
| `/api/v1/kb/documents/jobs/{id}` | GET | Extraction & vectorization status |
| `/api/v1/kb/search` | POST | Hybrid semantic retrieval (<80ms response) |
| `/ws/v1/voice/chat` | WebSocket | Bidirectional audio streaming with 150ms barge-in |
| `/api/v1/admin/sources` | GET / POST | Registered regulatory portals (*.nbe.gov.et) |
| `/api/v1/admin/regulatory/pending` | GET | Pending regulatory diffs awaiting compliance sign-off |
| `/api/v1/admin/review/interactions` | GET | Review flagged customer interactions |
| `/api/v1/admin/review/interactions/{id}/promote` | POST | Promote verified expert answer to Golden Knowledge Base |
| `/api/v1/admin/export/training-data` | GET | PII-sanitized ShareGPT JSONL training dataset export |

---

## 🐳 Production VPS Deployment

```bash
# Verify docker compose configuration
docker compose -f docker-compose.vps.yml config

# Build and start all containers in background
docker compose -f docker-compose.vps.yml up -d --build

# Run automated post-deploy smoke test
./scripts/vps_smoke_test.sh http://localhost:5000
```
