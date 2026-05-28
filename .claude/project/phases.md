# Delivery phases

ReviewAgent PTIT currently uses three delivery phases. Do not convert the five architecture layers into five phases.

## Phase 1 — PoC
- Status: implemented base / maintenance scope.
- Goal: prove the minimal backend + AI flow end-to-end.
- Flow: DOI submission -> Crossref -> OpenAlex fallback -> CMS -> grounded decision -> DB/API -> tests/eval.
- Active architecture coverage: Layer 1 and a minimal part of Layer 5.
- Default for Phase 1 maintenance tasks: keep changes inside this slice.

### Phase 1 includes
- config and environment loading
- submission, CMS, and decision schemas
- Crossref connector
- OpenAlex fallback connector
- metadata agent
- decision agent
- sequential orchestration or equivalent pipeline
- minimal database persistence
- FastAPI endpoints for submission, decision lookup, and health
- focused tests and evaluation script

### Phase 1 excludes
- frontend/dashboard
- reviewer queues, appeals, reports, and exports
- ORCID, ROR, author disambiguation, and affiliation matching
- journal ranking, predatory journal snapshots, and advanced journal validation
- integrity detection
- Celery-first async workflow
- observability stack and production deployment

## Phase 2 — MVP
- Status: active setup when the user asks for Phase 2/MVP work.
- Goal: expand the PoC into a usable internal system with broader verification and reviewer support.
- Flow: DOI + claimed author/affiliation -> Redis DOI cache -> LangGraph fan-out -> metadata + journal + author checks -> aggregator -> decision v2 -> DB/WORM audit -> API response or reviewer queue.
- Active architecture coverage: Layers 1, 2, 3, initial Layer 4 retraction evidence, and richer Layer 5 HITL decisioning.
- Detailed source: `DOCUMENT/phase2_guide.md`; concise execution scope: `.claude/project/phase2-scope.md`.

### Phase 2 includes
- CMS v2.0 with journal, author/affiliation, and retraction fields
- journal quality checks using MJL, SCImago, DOAJ, Beall/hijack evidence
- author and affiliation verification using ORCID, ROR, and Vietnamese-name matching
- Redis DOI cache with 24h TTL
- LangGraph fan-out/fan-in orchestration
- router, journal, author, aggregator, and decision v2 agent work
- decision v2 with grounded sub-scores, calibrated confidence, CoVe/self-consistency where useful
- WORM audit log and reviewer queue endpoints
- Celery/Redis background task support where needed
- Prometheus metrics, Langfuse tracing, Alembic migrations, tests, and eval

### Phase 2 excludes
- frontend/dashboard implementation unless separately requested
- appeals and reports
- full content-integrity pipelines beyond retraction evidence
- Kubernetes or production-grade rollout
- production compliance/SSO hardening
- self-hosted or multi-provider LLM strategy

## Phase 3 — Production
- Status: roadmap/future unless explicitly requested.
- Goal: operate the system reliably at scale with compliance, observability, advanced detection, and appeal handling.
- Likely scope: integrity pipelines, appeal workflows, multi-provider/self-hosted model strategy, production observability, compliance governance, and rollout architecture.

## Default implementation rule
If the user asks for Phase 2, use `.claude/project/phase2-scope.md` and `DOCUMENT/phase2_guide.md`. If the user asks for ambiguous maintenance or bug fixes, first classify whether it is Phase 1 base maintenance or Phase 2 MVP work. Clarify before implementing Phase 3 scope.
