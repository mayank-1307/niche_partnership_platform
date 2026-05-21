# Company Intelligence Extractor

Production-ready full-stack AI application that analyzes a company domain using a two-agent architecture, enriches findings with web search, and exports strict structured JSON.

## Stack

- Frontend: React + Vite + TailwindCSS + Framer Motion + Lucide React
- Backend: FastAPI + asyncio + httpx + BeautifulSoup + trafilatura + newspaper3k
- LLM: Mistral API
- Storage: Local filesystem JSON artifacts (no DB)

## Project Structure

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ agents/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ models/
│  │  └─ services/
│  ├─ requirements.txt
│  └─ storage/
├─ frontend/
│  ├─ src/
│  │  ├─ components/
│  │  └─ lib/
│  └─ package.json
└─ .env.example
```

## Agent Architecture

1. Agent 1: Company Intelligence Agent
- Crawls company pages (homepage + relevant pages + sitemap)
- Respects `robots.txt`
- Extracts readable text using `trafilatura`
- Enriches with configurable search provider (`duckduckgo`, `tavily`, `serper`)
- Uses Mistral to produce summarized research object + confidence notes + evidence

2. Agent 2: JSON Structuring Agent
- Converts research object into strict required schema
- Validates shape through Pydantic
- Fills safe defaults for missing values
- Produces final downloadable JSON

## API Endpoints

- `GET /health` - service health check
- `POST /analyze-company` - run full two-agent analysis
- `GET /download-json/{id}` - download generated JSON artifact

### Example Request

```bash
curl -X POST http://localhost:8000/analyze-company \
  -H "Content-Type: application/json" \
  -d '{"domain":"https://www.glean.com"}'
```

## Environment Variables

Create `.env` in project root using `.env.example`:

```env
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-large-latest
SEARCH_PROVIDER=duckduckgo
TAVILY_API_KEY=
SERPER_API_KEY=
BACKEND_CORS_ORIGINS=http://localhost:5173
```

Frontend env (`frontend/.env`):

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Backend Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## UI Features

- Modern dark AI SaaS interface
- Glassmorphism cards + gradient atmosphere
- Animated hero and cards with Framer Motion
- Agent activity panel
- JSON preview with copy and download
- Evidence/source list with links
- Toast notifications and error handling
- Mobile responsive layout

## Production Notes

- API client includes timeout + retries for Mistral calls
- Crawler limits pages and de-duplicates URLs
- Search provider configurable by env
- JSON outputs stored under `backend/storage`

## Screenshots

- `[Placeholder] Hero and Input Section`
- `[Placeholder] Agent Activity + Summary`
- `[Placeholder] JSON Preview + Evidence`

## Health Check

```bash
curl http://localhost:8000/health
```

## License

Internal / project-specific.
