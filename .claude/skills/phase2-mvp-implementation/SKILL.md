---
name: phase2-mvp-implementation
description: Use when implementing ReviewAgent PTIT Phase 2 MVP backend/AI work: CMS v2.0, journal/author agents, LangGraph fan-out, Redis/Celery, WORM audit, reviewer API, observability, tests, and eval.
when_to_use: Use for coding tasks that explicitly target Phase 2 MVP or reference DOCUMENT/phase2_guide.md implementation slices.
---

## Required context
Read before implementation:
- `CLAUDE.md`
- `.claude/project/phase2-scope.md`
- `.claude/project/current-state.md`
- `.claude/project/workflows.md`
- `DOCUMENT/phase2_guide.md`
- directly relevant files under `src/reviewagent/`, `scripts/`, and `tests/`

# Purpose
Implement the smallest correct Phase 2 MVP slice while preserving the project rules: grounding before generation, deterministic before stochastic, fail-safe review, and auditability.

## Phase 2 target flow
`submit DOI + claimed author/affiliation -> cache/source fetch -> metadata/journal/author checks -> aggregate evidence -> decision -> DB/audit -> API/reviewer handling`

## Rules
- Do not assume placeholder files are implemented.
- Prefer schemas, deterministic checks, connectors, and snapshots before LLM behavior.
- Keep LLM prompts evidence-only; never ask the model to invent metadata, indexing, quartile, ORCID, ROR, or retraction facts.
- Use `REVIEW` for incomplete, weak, or conflicting evidence.
- Add migrations/tests when persistence or API behavior changes.
- Keep Phase 3 concerns out unless the user explicitly requests them.

## Out of scope by default
- frontend dashboard
- appeals/reporting workflow
- full content-integrity pipeline beyond retraction checks
- Kubernetes/production deployment
- self-hosted or multi-provider LLM strategy

## Verification checklist
- Is the changed slice in Phase 2 and not Phase 3?
- Are all external facts grounded in API/snapshot/user input?
- Did tests cover success and degraded/fail-safe paths?
- Did persistence/API changes include appropriate schema alignment?
- Did any major milestone update `.claude/project/current-state.md`?
