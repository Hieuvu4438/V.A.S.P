# Current repository state

This file is a lightweight context snapshot for Claude Code. Verify current files before relying on it, and update it after major implementation milestones.

## Observed implementation state
The repository has a feature-complete Phase 1 PoC base. Phase 2 MVP context, skills, and agents are now set up under `.claude`, but most Phase 2 application modules are still placeholder-only until implemented.

Real implemented areas include:
- `src/reviewagent/config.py` — application, database, API, and LLM settings.
- `src/reviewagent/schemas/submission.py` — submission request/response schemas and DOI normalization.
- `src/reviewagent/schemas/cms.py` — canonical metadata schema with DOI, provenance, journal, author, and publication date validation.
- `src/reviewagent/schemas/decision.py` — structured decision output with confidence, rationale, flags, and sub-scores.
- `src/reviewagent/connectors/base.py` — async httpx base connector with timeout and error handling.
- `src/reviewagent/connectors/crossref.py` — Crossref REST API connector with DOI lookup and CMS mapping.
- `src/reviewagent/connectors/openalex.py` — OpenAlex API connector with DOI lookup and CMS mapping.
- `src/reviewagent/agents/state.py` — ReviewState dataclass for pipeline state.
- `src/reviewagent/agents/metadata_agent.py` — Metadata agent with Crossref → OpenAlex fallback.
- `src/reviewagent/agents/decision_agent.py` — Decision agent with LLM and rule-based fallback paths.
- `src/reviewagent/agents/graph.py` — Sequential pipeline orchestration (metadata → decision).
- `src/reviewagent/llm/gateway.py` — LLM gateway with decision generation and structured parsing.
- `src/reviewagent/llm/prompts/decision_v1.py` — Decision prompt v1 with grounding constraints.
- `src/reviewagent/llm/calibration.py` — Basic calibration stub (identity function).
- `src/reviewagent/db/session.py` — Async SQLAlchemy engine and session.
- `src/reviewagent/db/models/submission.py` — Submission ORM model.
- `src/reviewagent/db/models/publication.py` — Publication ORM model with JSONB CMS cache.
- `src/reviewagent/db/models/decision.py` — Decision ORM model with confidence and evidence.
- `src/reviewagent/db/repositories/submission_repo.py` — Submission CRUD operations.
- `src/reviewagent/db/repositories/decision_repo.py` — Decision CRUD operations.
- `src/reviewagent/api/main.py` — FastAPI app factory with lifespan.
- `src/reviewagent/api/deps.py` — DB session and pipeline dependencies.
- `src/reviewagent/api/routers/health.py` — GET /health endpoint.
- `src/reviewagent/api/routers/submissions.py` — POST /submissions endpoint.
- `src/reviewagent/api/routers/decisions.py` — GET /decisions/{id} and GET /decisions?submission_id= endpoints.
- `scripts/eval.py` — Evaluation script.
- `scripts/migrate.py` — DB table creation script.
- `tests/unit/test_schemas.py` — Unit coverage for schema behavior (6 tests).
- `pyproject.toml` — Project configuration with Phase 1 dependencies.
- `.env.example` — Environment template.
- `docker/docker-compose.yml` — PostgreSQL dev environment.
- `README.md` — Getting started guide.

Placeholder-only files (empty stubs for later phases):
- `src/reviewagent/agents/router_agent.py`, `journal_agent.py`, `author_agent.py`, `integrity_agent.py`, `appeal_agent.py`
- `src/reviewagent/connectors/doaj.py`, `orcid.py`, `retraction_watch.py`, `ror.py`
- `src/reviewagent/snapshots/` (all files)
- `src/reviewagent/author_nd/` (all files)
- `src/reviewagent/integrity/` (all files)
- `src/reviewagent/tasks/` (all files)
- `src/reviewagent/cache/` (all files)
- `src/reviewagent/audit/` (all files)
- `src/reviewagent/observability/` (all files)
- `src/reviewagent/api/routers/reviews.py`, `appeals.py`, `reports.py`
- `src/reviewagent/api/middleware.py`
- `src/reviewagent/db/models/user.py`, `journal.py`, `audit_log.py`
- `src/reviewagent/db/repositories/journal_repo.py`
- `src/reviewagent/schemas/audit.py`, `author.py`, `journal.py`
- `src/reviewagent/llm/prompts/appeal_v1.py`, `metadata_v1.py`

## Phase status
Phase 1 PoC is feature-complete as the base implementation. The explicit Phase 2 MVP setup now exists in `.claude/project/phase2-scope.md`, `.claude/skills/run-phase2-task`, `.claude/skills/phase2-mvp-implementation`, and `.claude/agents/phase2-mvp-implementer`. Verify application code before assuming any Phase 2 module is implemented.

## Phase 1 completion status
Phase 1 PoC is now feature-complete. The full flow works:
`POST /submissions (DOI) -> Crossref -> OpenAlex fallback -> CMS -> decision -> DB -> response`

## Documentation
- `DOCUMENT/phase1_guide.md` — Complete Phase 1 guide (business logic, run instructions, data flow, file roles, coding order, tests, checklist)
- `DOCUMENT/phase2_guide.md` — Phase 2 MVP planning guide (LangGraph parallel, journal/author agents, snapshots, Redis, Celery, audit WORM, observability, reviewer HITL)
- `DOCUMENT/phase3_guide.md` — Phase 3 Production planning guide (integrity detection, appeal workflow, multi-provider LLM, self-hosted LLM, Kubernetes, CI/CD eval gate, compliance)

Missing for full production readiness (but not in Phase 1 scope):
- Tests for connectors, agents, API endpoints, and integration
- Platt scaling calibration (currently identity function)
