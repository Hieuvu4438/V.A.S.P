# Delivery phases

ReviewAgent PTIT currently uses three delivery phases. Do not convert the five architecture layers into five phases.

## Phase 1 — PoC
- Status: active implementation target.
- Goal: prove the minimal backend + AI flow end-to-end.
- Flow: DOI submission -> Crossref -> OpenAlex fallback -> CMS -> grounded decision -> DB/API -> tests/eval.
- Active architecture coverage: Layer 1 and a minimal part of Layer 5.
- Default for ambiguous coding tasks: implement only this phase.

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
- Status: roadmap/future unless explicitly requested.
- Goal: expand the PoC into a usable internal system with broader verification and reviewer support.
- Likely scope: richer source coverage, journal quality checks, author/affiliation verification, reviewer operations, audit log improvements, and stronger deployment setup.

## Phase 3 — Production
- Status: roadmap/future unless explicitly requested.
- Goal: operate the system reliably at scale with compliance, observability, advanced detection, and appeal handling.
- Likely scope: integrity pipelines, appeal workflows, multi-provider/self-hosted model strategy, production observability, compliance governance, and rollout architecture.

## Default implementation rule
If the user asks to implement a feature and does not specify a phase, keep the implementation inside Phase 1. If the requested behavior naturally belongs to Phase 2 or Phase 3, clarify scope before implementing.
