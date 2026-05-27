# Phase 1 PoC Backend and AI Testing Guide

This guide explains how to run and understand the current Phase 1 backend service end to end.

It is written for two audiences:

- non-technical readers who want to understand what happens in the pipeline
- developers who need exact commands to test the backend, AI decision path, database persistence, and API responses

## 0. Phase 1 in plain language

Phase 1 verifies a submitted scientific publication using its DOI.

A DOI is like a permanent ID card for a paper. The system receives the DOI, looks it up in trusted publication databases, standardizes the returned information, asks the decision logic to judge the evidence, saves the result, and returns a response through the backend API.

The full Phase 1 flow is:

```text
User submits DOI
  -> Backend API receives the DOI
  -> System creates a submission record in PostgreSQL
  -> Metadata agent searches Crossref first
  -> If Crossref has no usable result, metadata agent searches OpenAlex
  -> Result is normalized into the Canonical Metadata Schema
  -> Decision agent reviews only the collected evidence
  -> Decision uses LLM mode when configured, otherwise rule fallback
  -> Publication and decision are saved in PostgreSQL
  -> Backend API returns submission_id, status, and decision_id
  -> User can fetch the saved decision later
```

Simple summary:

```text
DOI in -> trusted metadata lookup -> clean metadata -> AI/rule decision -> database save -> API response out
```

## 1. What each pipeline part does

### 1.1 Backend API

The backend API is the service that receives requests from users or other software.

In Phase 1, the important endpoints are:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Checks whether the backend service is running |
| `POST /submissions` | Submits a DOI and runs the full verification pipeline |
| `GET /decisions?submission_id=<id>` | Fetches the saved decision for a submission |
| `GET /decisions/<decision_id>` | Fetches a saved decision by decision ID |

### 1.2 Metadata lookup

After a DOI is submitted, the system searches external academic metadata sources.

Lookup order:

```text
1. Crossref
2. OpenAlex, only if Crossref does not return usable metadata
```

Crossref is checked first because it is an authoritative DOI metadata source. OpenAlex is the fallback source.

The metadata may include:

- DOI
- title
- publication year
- publication date
- journal name
- ISSN
- publisher
- authors
- whether the paper is retracted
- source API used, such as `crossref` or `openalex`

### 1.3 Canonical Metadata Schema

Crossref and OpenAlex return data in different shapes. The system converts their responses into one common internal shape called the Canonical Metadata Schema.

In simple terms:

```text
Different source formats -> one clean PTIT metadata format
```

This keeps the decision step simple and grounded.

### 1.4 Decision agent

The decision agent receives the cleaned metadata and returns a structured decision.

Possible decisions:

| Decision | Meaning |
| --- | --- |
| `APPROVE` | The metadata is strong enough for automatic approval |
| `REVIEW` | The metadata is incomplete, uncertain, or needs human checking |
| `REJECT` | The evidence clearly shows a serious problem, such as retraction |

Important rule:

```text
The decision must be based on fetched metadata, not model memory or guessing.
```

### 1.5 AI server / LLM mode

Phase 1 can use OpenRouter as the LLM provider.

When `LLM__API_KEY` is configured, the decision agent sends the cleaned metadata to the LLM and asks for a structured JSON decision.

The LLM does not fetch metadata by itself. It only reviews the evidence already collected by the backend.

AI mode flow:

```text
DOI
  -> Crossref/OpenAlex metadata
  -> Canonical Metadata Schema
  -> OpenRouter LLM decision request
  -> structured decision JSON
  -> PostgreSQL save
  -> API response
```

### 1.6 Rule fallback mode

If `LLM__API_KEY` is empty, invalid, or the LLM call fails, the system still returns a decision using deterministic rule-based logic.

Rule fallback checks signals such as:

- whether the source is Crossref or OpenAlex
- whether ISSN exists
- whether publisher exists
- whether authors exist
- whether the publication is retracted
- whether metadata lookup produced errors

Fallback mode is important because the backend should still work even when the AI provider is unavailable.

Fallback flow:

```text
DOI
  -> Crossref/OpenAlex metadata
  -> Canonical Metadata Schema
  -> local rule-based decision
  -> PostgreSQL save
  -> API response
```

## 2. Prepare the environment

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

To test rule-based fallback behavior, leave the API key empty:

```env
LLM__API_KEY=
```

## 3. Run quick automated checks first

Run the full automated test suite:

```powershell
pytest tests/ -v
```

This checks schemas, connectors, agents, and integration tests.

If you want to test each part separately, use the commands below.

### 3.1 Schemas

```powershell
pytest tests/unit/test_schemas.py -v
```

This validates the data contracts for canonical metadata, decisions, and submissions.

### 3.2 Metadata connectors

```powershell
pytest tests/unit/test_connectors.py -v
```

This validates Crossref and OpenAlex parsing and mapping into the canonical metadata shape.

### 3.3 Agents

```powershell
pytest tests/unit/test_agents.py -v
```

This validates metadata agent and decision agent behavior, including safe fallback behavior when LLM usage is unavailable or unsuitable.

Relevant files if this fails:

```text
src/reviewagent/agents/metadata_agent.py
src/reviewagent/agents/decision_agent.py
src/reviewagent/llm/gateway.py
```

### 3.4 Review pipeline integration

```powershell
pytest tests/integration/test_review_pipeline.py -v
```

This validates the sequential Phase 1 pipeline:

```text
submission_id + DOI -> metadata -> decision -> ReviewState
```

Relevant file if this fails:

```text
src/reviewagent/agents/graph.py
```

## 4. Run the pipeline without starting the API server

Use the evaluation script when you want to test the pipeline quickly without running FastAPI and PostgreSQL manually.

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

## 5. Run the full backend service pipeline

Use this section when you want to test the real backend service with PostgreSQL, API endpoints, metadata lookup, decision generation, and persistence.

### 5.1 Start PostgreSQL

```powershell
docker compose -f docker/docker-compose.yml up -d
```

PostgreSQL stores submissions, publications, and decisions.

### 5.2 Apply database migrations

```powershell
python scripts/migrate.py upgrade
```

This prepares the database tables needed by the backend.

### 5.3 Start the FastAPI backend server

```powershell
uvicorn reviewagent.api.main:app --reload --port 8000
```

Keep this terminal open. Use a second terminal for API checks.

### 5.4 Check that the backend is alive

```powershell
curl http://localhost:8000/health
```

A successful response means the FastAPI app is running.

### 5.5 Submit a DOI and run the full pipeline

```powershell
curl -X POST http://localhost:8000/submissions `
  -H "Content-Type: application/json" `
  -d "{\"doi\": \"10.1109/5.771073\"}"
```

What happens after this request:

```text
1. API receives the DOI.
2. Backend creates a submission with PROCESSING status.
3. Metadata agent checks Crossref.
4. If Crossref fails, metadata agent checks OpenAlex.
5. Metadata is normalized into the Canonical Metadata Schema.
6. Decision agent uses LLM mode if configured.
7. If LLM is not configured or fails, rule fallback is used.
8. Publication metadata is saved.
9. Decision is saved.
10. Submission status becomes COMPLETED.
11. API returns IDs for later lookup.
```

Expected response shape:

```json
{
  "submission_id": "<uuid>",
  "status": "COMPLETED",
  "decision_id": "<uuid>"
}
```

If the DOI cannot be found from Crossref or OpenAlex, the endpoint may return `422` with metadata lookup errors.

### 5.6 Fetch decision by submission ID

Use the `submission_id` returned from the previous step:

```powershell
curl "http://localhost:8000/decisions?submission_id=<submission_id>"
```

Expected response shape:

```json
{
  "decision_id": "<uuid>",
  "submission_id": "<uuid>",
  "decision": "APPROVE",
  "confidence_raw": 0.8,
  "confidence_calibrated": 0.8,
  "rationale": "Metadata is reasonably complete from an authoritative source.",
  "flags": [],
  "evidence": {
    "sub_scores": {
      "metadata_completeness": 1.0,
      "source_reliability": 0.8
    }
  }
}
```

The exact numbers and rationale can differ depending on the metadata source and whether LLM mode or rule fallback mode was used.

### 5.7 Fetch decision by decision ID

Use the `decision_id` returned by `/submissions`:

```powershell
curl http://localhost:8000/decisions/<decision_id>
```

This should return the same saved decision record.

## 6. Test AI mode and fallback mode

### 6.1 Test LLM-backed decision mode

Set a valid key and model in `.env`:

```env
LLM__API_KEY=<your-openrouter-api-key>
LLM__MODEL=nvidia/nemotron-3-super-120b-a12b:free
```

Restart the API server after changing `.env`.

Then test either through the evaluation script:

```powershell
python scripts/eval.py
```

or through the backend API:

```powershell
curl -X POST http://localhost:8000/submissions `
  -H "Content-Type: application/json" `
  -d "{\"doi\": \"10.1109/5.771073\"}"
```

Expected behavior:

```text
The backend fetches metadata first, then sends only that cleaned metadata to the LLM for decision generation.
```

### 6.2 Test rule-based fallback mode

Set:

```env
LLM__API_KEY=
```

Restart the API server or rerun the eval script.

Then run:

```powershell
python scripts/eval.py
```

or submit a DOI through `/submissions`.

Expected behavior:

```text
The system still returns a decision without calling the LLM.
```

This proves the backend is not fully dependent on the AI provider.

## 7. Recommended full verification order

Use this order when checking the whole Phase 1 backend:

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

Then use a second terminal:

```powershell
curl http://localhost:8000/health
curl -X POST http://localhost:8000/submissions `
  -H "Content-Type: application/json" `
  -d "{\"doi\": \"10.1109/5.771073\"}"
```

Finally, fetch the decision:

```powershell
curl "http://localhost:8000/decisions?submission_id=<submission_id>"
```

## 8. How to explain a successful full run

A successful full backend run means:

```text
The user submitted a DOI.
The backend found publication metadata from Crossref or OpenAlex.
The metadata was converted into the project standard format.
The decision agent produced APPROVE, REVIEW, or REJECT.
The publication and decision were saved in PostgreSQL.
The API returned a completed response.
The saved decision could be fetched again later.
```

Example human-readable result:

```text
The DOI was found in Crossref. The system found the title, author list, journal, publisher, and publication year. Because the metadata is complete enough and comes from an authoritative source, the system returned APPROVE and saved the decision.
```

Another possible result:

```text
The DOI was found, but some important metadata was missing. The system returned REVIEW so a human can check it manually.
```

## 9. Failure guide

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

## 10. Definition of a healthy Phase 1 run

A healthy Phase 1 backend run should satisfy all of the following:

- `pytest tests/ -v` passes.
- `python scripts/eval.py` returns a JSON report without pipeline errors.
- PostgreSQL starts successfully.
- Migrations apply successfully.
- `GET /health` succeeds.
- `POST /submissions` with a known DOI returns `COMPLETED` and a `decision_id`.
- `GET /decisions?submission_id=<submission_id>` returns the persisted decision.
- The system returns a decision when `LLM__API_KEY` is configured.
- The system still returns a decision when `LLM__API_KEY` is empty, using rule-based fallback.
