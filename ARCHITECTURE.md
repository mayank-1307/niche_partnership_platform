# Niche Partnership Platform Architecture

## Overview

This project is a full-stack AI-powered company intelligence extractor.

- Frontend: React + Vite + TailwindCSS + Framer Motion
- Backend: FastAPI + asynchronous services + Pydantic schema validation
- AI: Mistral / Gemini via OpenAI-compatible API client
- Storage: filesystem JSON artifacts + optional PostgreSQL company profile storage
- File ingest: PDF / DOCX / text uploads support

## High-Level Flow

1. User enters a company domain in the frontend UI or uploads a document.
2. Frontend sends a request to backend `POST /analyze-company`.
3. Backend orchestrator runs a two-agent pipeline:
   - Agent 1: company intelligence gathering
   - Document intelligence agent: extract facts from uploaded doc (optional)
   - Agent 2: strict JSON structuring and gating
4. Backend persists results to disk and optionally PostgreSQL.
5. Frontend renders summary, evidence, structured JSON, and logs.

## Key Components

### Frontend

- `frontend/src/App.tsx` — main page, input, result rendering, recent profile list.
- `frontend/src/lib/api.ts` — API client for backend endpoints.
- `frontend/src/components/` — UI components and JSON viewer.

### Backend

- `backend/app/main.py` — FastAPI app setup, CORS, startup lifecycle.
- `backend/app/api/routes.py` — HTTP routes and request parsing.
- `backend/app/services/orchestrator.py` — main analysis workflow.
- `backend/app/agents/agent1_company_intelligence.py` — first AI agent.
- `backend/app/agents/agent_document_intelligence.py` — optional document extraction agent.
- `backend/app/agents/agent2_json_structuring.py` — second AI agent for strict JSON.
- `backend/app/services/search_service.py` — query search provider / web hits.
- `backend/app/services/llm_agent_runtime.py` — provider-agnostic LLM runtime logic.
- `backend/app/services/mistral_client.py` — wrapper to call `llm_agent_runtime`.
- `backend/app/services/storage_service.py` — JSON output persistence.
- `backend/app/services/db_service.py` — optional PostgreSQL persistence.
- `backend/app/services/document_ingestion_service.py` — parse uploaded documents.
- `backend/app/models/schemas.py` — Pydantic schemas, structured JSON models, API responses.
- `backend/app/core/config.py` — environment config and runtime settings.

## End-to-End Request Flow

### 1. User input and frontend request

- `App.tsx` collects `domain` and optional `sourceDocument`.
- `analyzeCompany(domain, sourceDocument)` in `frontend/src/lib/api.ts`:
  - If file exists, sends multipart/form-data with `domain` and `document`.
  - Otherwise sends JSON `{ domain }`.
- API base URL comes from `VITE_API_BASE_URL`.

### 2. Backend receives request

- `backend/app/api/routes.py` handles `POST /analyze-company`.
- `_parse_analysis_request` parses JSON or form-data.
- `normalize_domain` sanitizes domain input.
- Calls `analysis_orchestrator.run(domain, uploaded_document)`.

### 3. Orchestrator workflow

- `backend/app/services/orchestrator.py` orchestrates the pipeline.
- Creates `AgentLog` entries for traceability.
- Calls:
  1. `company_intelligence_agent.run(domain, logs, uploaded_document)`
  2. If document uploaded, `document_intelligence_agent.run(uploaded_document, logs)`
  3. `json_structuring_agent.run(research, logs)`
- Merges uploaded document evidence and summary into research payload.

### 4. Agent 1: Company Intelligence

- `backend/app/agents/agent1_company_intelligence.py`:
  - builds search queries from domain and company name hint.
  - uses `search_service.search(...)` to collect web hits.
  - prepares `AGENT1_SUMMARY_PROMPT` and calls `mistral_client.chat_json(...)`.
  - returns `ResearchObject` with:
    - `company_name`, `website`, `summary_markdown`
    - `extracted_insights`, `confidence_notes`, `evidence`
- If LLM fails, fallback summarization and insights are used.

### 5. Optional Document Intelligence Agent

- `backend/app/agents/agent_document_intelligence.py`:
  - extracts text from uploaded PDF/DOCX/TXT using `document_ingestion_service.py`.
  - calls `mistral_client.chat_json(...)` with `DOCUMENT_EXTRACTION_PROMPT`.
  - returns structured document insights and evidence.
- Orchestrator merges document findings into the research object.

### 6. Agent 2: JSON Structuring

- `backend/app/agents/agent2_json_structuring.py`:
  - compacts and truncates research payload.
  - calls `mistral_client.chat_json(...)` with `AGENT2_STRUCTURING_PROMPT`.
  - normalizes LLM JSON into `GateBasedCompanyAnalysis` schema.
  - attaches uploaded document sources to evidence sections.
  - ensures fallback evidence if no LLM sources returned.
- Produces strict company analysis JSON across these pillars:
  - `enterprise_credibility`
  - `strategic_relevance`
  - `delivery_feasibility`
  - `commercial_viability`
  - `evidence`

### 7. Persistence and output

- Backend saves structured JSON file via `json_storage_service.save(...)`.
- If `DATABASE_URL` is configured, saves profile into `company_profiles` table via `company_profile_db.save_company_profile(...)`.
- Returns `AnalyzeResponse` containing:
  - `id` (profile ID)
  - `company_summary`
  - `extracted_insights`
  - `evidence`
  - `structured_json`
  - `agent_logs`

### 8. Frontend rendering

- UI displays analysis result:
  - summary text
  - extracted insights and evidence sources
  - strict JSON preview via `JsonViewer`
  - agent logs and activity
- `downloadJsonUrl(id)` generates a download link for persisted JSON.

## Supporting Backend Endpoints

- `GET /health` — simple service health check.
- `GET /download-json/{file_id}` — download saved JSON artifact.
- `GET /stored-jsons` — list on-disk JSON outputs.
- `GET /stored-json/{file_id}` — read stored JSON output.
- `GET /decision-intelligence/profiles` — list saved company profiles.
- `GET /decision-intelligence/profiles/{profile_id}` — retrieve saved profile details.
- `GET /decision-intelligence/{file_id}` — evaluate a saved JSON against decision intelligence rules.
- `GET /scoring/{file_id}` — produce a scoring report from saved JSON.

## External Integrations

- Search Provider:
  - `duckduckgo` via `duckduckgo_search`
  - optional: `tavily` or `serper`
- LLM Provider:
  - default provider is `mistral`
  - optional provider `gemini`
- Document parsing:
  - PDF extraction via `pypdf` or manual PDF stream parsing
  - DOCX extraction via XML parsing

## Configuration

Backend env in `backend/.env` or root `.env`:

- `MISTRAL_API_KEY`
- `MISTRAL_MODEL`
- `SEARCH_PROVIDER`
- `TAVILY_API_KEY`
- `SERPER_API_KEY`
- `BACKEND_CORS_ORIGINS`
- `DATABASE_URL`

Frontend env in `frontend/.env`:

- `VITE_API_BASE_URL=http://localhost:8000`

## Copyable Architecture Flow Diagram

```mermaid
flowchart TD
  subgraph Frontend
    UI[User Interface]\n    UI -->|enter domain + upload docs| APIClient[API Client `frontend/src/lib/api.ts`]
  end

  APIClient -->|POST /analyze-company| BackendAPI[FastAPI `backend/app/api/routes.py`]

  subgraph Backend
    BackendAPI -->|parse request| Orchestrator[`analysis_orchestrator`]\n    Orchestrator -->|run Agent 1| Agent1[`agent1_company_intelligence.py`]
    Agent1 --> Search[Search Service `search_service.search()`]
    Search --> ExternalSearch[DuckDuckGo / Tavily / Serper]
    Agent1 -->|LLM prompt| LLMRuntime[`mistral_client -> llm_agent_runtime`]
    Orchestrator -->|optional uploaded doc| DocAgent[`agent_document_intelligence.py`]
    DocAgent -->|LLM prompt| LLMRuntime
    Orchestrator -->|run Agent 2| Agent2[`agent2_json_structuring.py`]
    Agent2 -->|LLM prompt| LLMRuntime
    Agent2 --> JSONModel[`GateBasedCompanyAnalysis schema`]
    Orchestrator -->|save JSON| Storage[`json_storage_service`]
    Orchestrator -->|save DB profile| DB[`company_profile_db`]
  end

  BackendAPI -->|return response| UI
  Storage -->|download endpoint| BackendAPI
  DB -->|profile endpoints| BackendAPI

  style Backend fill:#f3f4f6,stroke:#9ca3af
  style Frontend fill:#eef2ff,stroke:#6366f1
```

## Architecture Summary for ChatGPT

Use this section as a direct prompt to generate architecture diagrams or explanations.

- React frontend collects domain input and optional document upload.
- Frontend sends request to FastAPI backend at `/analyze-company`.
- FastAPI routes parse JSON or multipart form uploads.
- The orchestrator runs a two-agent AI pipeline:
  - Agent 1 collects web evidence using search provider queries.
  - Optional Document Intelligence agent extracts uploaded-document facts.
  - Agent 2 normalizes and gates research into a strict JSON schema.
- LLM calls are handled by `llm_agent_runtime`, supporting Mistral or Gemini.
- Output persists as a JSON file and optionally in PostgreSQL.
- Additional endpoints support JSON download, stored file listing, profile listing, decision intelligence, and scoring.

## Notes

- No code changes were made to the project.
- The architecture document is generated from the existing project structure and implementation files.
