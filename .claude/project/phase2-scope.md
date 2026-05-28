# Phase 2 MVP scope

This file describes the active Phase 2 MVP delivery slice. Use `DOCUMENT/phase2_guide.md` as the detailed source of truth, but keep this file concise and operational.

## Status
- Phase 1 PoC is complete enough to serve as the base implementation.
- Phase 2 MVP is the active setup and planning context when the user explicitly asks for Phase 2 work.
- Actual code may still be Phase 1 plus placeholders; verify files before assuming Phase 2 modules are implemented.

## Goal
Expand the DOI-based PoC into an internal PTIT MVP that can run on one VM, support reviewer handling, and verify submissions with richer grounded evidence.

## Target flow
`DOI + claimed author/affiliation -> validate -> Redis DOI cache -> LangGraph fan-out -> metadata + journal + author checks -> aggregator -> decision -> DB -> WORM audit -> API response / reviewer queue`

## In scope
- CMS v2.0 fields for journal indexing, author ORCID/ROR, abstract/article details, and retraction status
- journal schemas and checks using MJL, SCImago, DOAJ, Beall/hijack evidence
- author schemas and checks using ORCID, ROR, and Vietnamese-name disambiguation
- Retraction Watch or offline retraction evidence as an initial integrity signal
- Redis DOI cache with 24h TTL
- LangGraph-style orchestration with router, metadata, journal, author, aggregator, and decision agents
- decision v2 using grounded sub-scores, CoVe/self-consistency where appropriate, calibrated confidence, and fail-safe `REVIEW`
- WORM audit log with HMAC chain
- reviewer queue endpoints for review, assignment, and manual decision override
- Celery/Redis background tasks where the pipeline should not block requests
- Prometheus metrics and Langfuse tracing as MVP observability
- Alembic migrations for new database models
- snapshot seed/update scripts and Phase 2 tests/eval

## Explicit non-goals for Phase 2
- frontend dashboard implementation unless separately requested
- full content-integrity detection beyond retraction signals
- appeals workflow and reports exports
- Kubernetes or production-grade deployment
- full compliance governance and production SSO hardening
- self-hosted or multi-provider LLM strategy

## Guardrails
- Grounding before generation: every field used by the LLM must come from connector, snapshot, database, or user input.
- Deterministic before stochastic: exact DOI/source/journal/author checks run before LLM decisioning.
- Cache before fetch where safe: reuse DOI metadata for 24h; do not cache uncertain final decisions as fact.
- Fail safe: weak, missing, or conflicting evidence routes to `REVIEW`.
- Audit every important state transition: submission creation, system decision, reviewer override.
- Keep MVP implementation incremental; do not jump to Phase 3 infrastructure.

## Verification targets
- focused unit tests for schemas, snapshots, author matching, journal scoring, and WORM audit
- integration tests for Phase 2 pipeline and reviewer API
- eval script over a gold dataset when available
- target metrics from the guide: F1 >= 0.88, average latency < 15s, cost <= 0.05 USD/submission
