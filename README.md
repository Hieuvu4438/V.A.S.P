# ReviewAgent PTIT — Phase 1 PoC

AI-assisted scientific publication verification system for PTIT.

Current phase: **Phase 1 PoC** — backend + AI only, no frontend.

## Quick start

### 1. Setup environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set LLM__API_KEY if using LLM decision agent
```

### 3. Start PostgreSQL

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 4. Create database tables

```bash
python scripts/migrate.py upgrade
```

### 5. Run the app

```bash
uvicorn reviewagent.api.main:app --reload --port 8000
```

### 6. Test the API

```bash
# Submit a DOI for review
curl -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -d '{"doi": "10.1109/5.771073"}'

# Check health
curl http://localhost:8000/health

# Get decision
curl http://localhost:8000/decisions?submission_id=<uuid>
```

## Phase 1 flow

```
POST /submissions (DOI)
  -> Crossref connector
  -> OpenAlex fallback
  -> CMS normalization
  -> Decision agent (LLM or rule-based)
  -> DB persistence
  -> Response with decision
```

## Running tests

```bash
pytest tests/ -v
```

## Running eval

```bash
python scripts/eval.py
```

## Project structure (Phase 1)

- `src/reviewagent/schemas/` — Pydantic models (CMS, decision, submission)
- `src/reviewagent/connectors/` — Crossref and OpenAlex HTTP clients
- `src/reviewagent/agents/` — Metadata agent, decision agent, pipeline
- `src/reviewagent/llm/` — LLM gateway, prompts, calibration
- `src/reviewagent/db/` — SQLAlchemy async models and repositories
- `src/reviewagent/api/` — FastAPI routers and app factory
- `scripts/` — Migration, eval, and utility scripts
- `tests/` — Unit and integration tests
