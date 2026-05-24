# Phase 1 PoC Backend and AI Testing Guide

This guide explains how to test the current Phase 1 backend slice end to end and by individual component.

Phase 1 flow:

```text
DOI submission
  -> Crossref metadata lookup
  -> OpenAlex fallback when needed
  -> Canonical Metadata Schema normalization
  -> Decision agent, LLM-backed or rule fallback
  -> Database persistence
  -> FastAPI response
```

## 1. Prepare the environment

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Create a local environment file if it does not exist:

```powershell
Copy-Item .env.example .env
```

Set local secrets only in `.env`. Do not commit `.env`.

For LLM-backed decisions, configure:

```env
LLM__PROVIDER=openrouter
LLM__API_KEY=<your-openrouter-api-key>
LLM__MODEL=nvidia/nemotron-3-super-120b-a12b:free
LLM__OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM__TIMEOUT_SECONDS=60
```

To test rule-based fallback behavior, leave `LLM__API_KEY` empty.

## 2. Run the full automated test suite

```powershell
pytest tests/ -v
```

This is the fastest broad check that schemas, connectors, agents, and integration tests still work.

## 3. Test Phase 1 components individually

### 3.1 Schemas

```powershell
pytest tests/unit/test_schemas.py -v
```

Validates Pydantic contracts for canonical metadata, decisions, and submission-related data.

If this fails, inspect schema validation or test fixture data first.

### 3.2 Metadata connectors

```powershell
pytest tests/unit/test_connectors.py -v
```

Validates Crossref and OpenAlex response parsing and mapping into the canonical metadata shape.

If this fails, the problem is likely in external-source parsing or normalization logic.

### 3.3 Agents

```powershell
pytest tests/unit/test_agents.py -v
```

Validates metadata and decision agent behavior, including safe fallback behavior when LLM usage is unavailable or unsuitable.

If this fails, inspect:

```text
src/reviewagent/agents/metadata_agent.py
src/reviewagent/agents/decision_agent.py
src/reviewagent/llm/gateway.py
```

### 3.4 Review pipeline integration

```powershell
pytest tests/integration/test_review_pipeline.py -v
```

Validates the sequential Phase 1 pipeline:

```text
submission_id + DOI -> metadata -> decision -> ReviewState
```

If this fails, inspect:

```text
src/reviewagent/agents/graph.py
```

## 4. Run the evaluation script

Run the default evaluation dataset:

```powershell
python scripts/eval.py
```

Expected output is a JSON report with `rows` and `metrics`, for example:

```json
{
  "rows": [
    {
      "doi": "10.1109/5.771073",
      "expected": "APPROVE",
      "predicted": "APPROVE",
      "source": "crossref",
      "errors": [],
      "correct": true
    }
  ],
  "metrics": {
    "total": 1,
    "labeled": 1,
    "accuracy": 1.0
  }
}
```

To evaluate a custom dataset, create a JSON file with this shape:

```json
[
  {
    "doi": "10.1109/5.771073",
    "expected_decision": "APPROVE"
  }
]
```

Then run:

```powershell
python scripts/eval.py --dataset dataset.json --output eval_report.json
```

Keep temporary datasets and reports out of git unless they are intentionally added as test fixtures.

## 5. Test the FastAPI backend with PostgreSQL

### 5.1 Start PostgreSQL

```powershell
docker compose -f docker/docker-compose.yml up -d
```

### 5.2 Apply migrations

```powershell
python scripts/migrate.py upgrade
```

### 5.3 Start the API server

```powershell
uvicorn reviewagent.api.main:app --reload --port 8000
```

Use a second terminal for API checks.

### 5.4 Check health

```powershell
curl http://localhost:8000/health
```

A successful response means the FastAPI app is running.

### 5.5 Submit a DOI

```powershell
curl -X POST http://localhost:8000/submissions `
  -H "Content-Type: application/json" `
  -d "{\"doi\": \"10.1109/5.771073\"}"
```

Expected response shape:

```json
{
  "submission_id": "<uuid>",
  "status": "COMPLETED",
  "decision_id": "<uuid>"
}
```

### 5.6 Fetch decision by submission ID

```powershell
curl "http://localhost:8000/decisions?submission_id=<submission_id>"
```

Expected response shape:

```json
{
  "decision_id": "<uuid>",
  "submission_id": "<uuid>",
  "decision": "APPROVE",
  "confidence_raw": 0.0,
  "confidence_calibrated": 0.0,
  "rationale": "...",
  "flags": [],
  "evidence": {
    "sub_scores": {}
  }
}
```

### 5.7 Fetch decision by decision ID

```powershell
curl http://localhost:8000/decisions/<decision_id>
```

## 6. Test LLM and rule fallback modes

### 6.1 LLM-backed decision mode

Set a valid key and model in `.env`:

```env
LLM__API_KEY=<your-openrouter-api-key>
LLM__MODEL=nvidia/nemotron-3-super-120b-a12b:free
```

Restart the API server or rerun the eval script after changing `.env`.

Use:

```powershell
python scripts/eval.py
```

or submit a DOI through `/submissions`.

### 6.2 Rule-based fallback mode

Set:

```env
LLM__API_KEY=
```

Then run:

```powershell
python scripts/eval.py
```

The system should still return a decision using deterministic rule-based logic.

## 7. Recommended verification order

Use this order when diagnosing problems:

```powershell
pytest tests/unit/test_schemas.py -v
pytest tests/unit/test_connectors.py -v
pytest tests/unit/test_agents.py -v
pytest tests/integration/test_review_pipeline.py -v
python scripts/eval.py
docker compose -f docker/docker-compose.yml up -d
python scripts/migrate.py upgrade
uvicorn reviewagent.api.main:app --reload --port 8000
```

Then test:

```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/submissions `
  -H "Content-Type: application/json" `
  -d "{\"doi\": \"10.1109/5.771073\"}"
```

## 8. Failure guide

| Symptom | Likely area |
| --- | --- |
| `test_schemas.py` fails | Schema validation or test fixture shape |
| `test_connectors.py` fails | Crossref/OpenAlex parsing or mapping |
| `test_agents.py` fails | Metadata agent, decision agent, or LLM gateway behavior |
| `test_review_pipeline.py` fails | Pipeline orchestration in `ReviewPipeline` |
| `scripts/eval.py` fails | Live pipeline, external API access, or LLM/rule decision behavior |
| `/submissions` returns `422` | Metadata could not be fetched for the DOI |
| `/submissions` returns `500` | Pipeline or database persistence error |
| `/decisions?...` returns `404` | No saved decision for that submission ID or wrong ID |

## 9. Definition of a healthy Phase 1 run

A healthy Phase 1 backend run should satisfy all of the following:

- `pytest tests/ -v` passes.
- `python scripts/eval.py` returns a JSON report without pipeline errors.
- PostgreSQL starts successfully.
- Migrations apply successfully.
- `GET /health` succeeds.
- `POST /submissions` with a known DOI returns `COMPLETED` and a `decision_id`.
- `GET /decisions?submission_id=<submission_id>` returns the persisted decision.
- The system still returns a decision when `LLM__API_KEY` is empty, using rule-based fallback.
