# Phase 1 PoC scope

This file describes the **current implementation slice**, not the full product vision. For the broader project shape, see:
- `CLAUDE.md`
- `.claude/project/overview.md`
- `.claude/project/architecture.md`

## In scope
- project setup for backend PoC
- environment/config loading
- submission schema
- CMS schema
- decision schema
- Crossref connector
- OpenAlex fallback connector
- metadata agent
- decision agent
- sequential orchestration graph or equivalent pipeline
- database session and minimal models
- FastAPI endpoints for submission, decision lookup, and health
- unit and integration tests
- evaluation script

## Explicit non-goals
- frontend UI
- reviewer dashboard
- review queue and appeals
- reports and exports
- ORCID, ROR, and author disambiguation
- journal quality indexing and snapshot pipelines
- retraction or integrity detection systems
- Celery-first async architecture
- Prometheus, Grafana, Langfuse, OpenTelemetry
- Kubernetes or production infra

## Default implementation strategy
- choose the smallest version that works
- keep code local and simple
- avoid introducing abstractions for future phases unless the repo already requires them
- prefer adding tests for each non-trivial PoC component

## Safe defaults
- missing metadata -> fail safe
- weak evidence -> `REVIEW`
- missing external dependency -> surface clearly instead of faking success
