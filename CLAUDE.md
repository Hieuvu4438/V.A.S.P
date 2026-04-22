# ReviewAgent PTIT

## Project summary
- ReviewAgent PTIT is an AI-assisted system for scientific publication verification at PTIT.
- The long-term project is a multi-layer verification platform that combines authoritative metadata sources, AI agents, policy-aware decisioning, and human-in-the-loop review.
- The repository currently focuses on **Phase 1 PoC**, but context in this repo should reflect the **whole project roadmap**, not only the current slice being implemented.

## Full project vision
The project aims to verify publication submissions against authoritative sources and return structured decisions with evidence.

Core project capabilities across the roadmap:
- identity and source verification for publication metadata
- journal quality checks
- author and affiliation verification
- optional content integrity checks
- final decisioning with auditability and human review

## Current implementation phase
The active delivery target is **Phase 1 PoC**.

Phase 1 includes:
- submission input with DOI
- metadata fetch from Crossref first
- OpenAlex fallback if Crossref misses
- normalization into a grounded CMS
- decision generation from grounded evidence
- persistence in the database
- FastAPI endpoints
- tests and evaluation script

## Full-project architecture layers
1. Identity and source verification
2. Journal quality checks
3. Author and affiliation verification
4. Content integrity checks
5. Decision and human-in-the-loop workflow

## Current code focus
- `src/reviewagent/schemas/`
- `src/reviewagent/connectors/`
- `src/reviewagent/agents/`
- `src/reviewagent/llm/`
- `src/reviewagent/db/`
- `src/reviewagent/api/`
- `scripts/eval.py`
- `tests/`

## Usually out of scope unless explicitly requested
- frontend or dashboard work
- reviewer queue, appeals, reports
- ORCID and author disambiguation implementation
- journal quality snapshots and advanced journal validation
- integrity detection
- Celery, Redis-heavy async workflows, observability stack
- Kubernetes or production deployment work

## Core rules
- Grounding before generation: metadata must come from authoritative sources, not model memory.
- Deterministic before stochastic: validation and exact lookups should be code-first.
- Fail safe: if evidence is missing or conflicting, prefer `REVIEW` instead of overconfident approval.
- Keep changes minimal and appropriate to the requested phase.
- Do not silently expand a Phase 1 task into MVP or Production work.

## Key source documents
- `DOCUMENT/implementation_plan.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase1_poc_backend_ai_step_by_step_prompts.md`

## Recommended working pattern
1. Read the relevant files first.
2. Understand whether the request is about the full project or only the active phase.
3. Reuse existing repo structure instead of inventing new layout.
4. Add tests for non-trivial logic.
5. Keep prompts, schemas, and connectors grounded and simple.

## Important paths
- `src/reviewagent/` — application code
- `scripts/` — evaluation and data scripts
- `tests/` — unit and integration tests
- `DOCUMENT/` — project planning and implementation guidance
- `.claude/project/` — distilled project context
- `.claude/skills/` — reusable Claude Code workflows
