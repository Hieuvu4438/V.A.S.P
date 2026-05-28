---
name: run-phase2-task
description: Use as the general Phase 2 MVP playbook for ReviewAgent PTIT work involving LangGraph orchestration, journal checks, author verification, Redis/Celery, audit, reviewer endpoints, observability, tests, or eval.
when_to_use: Use when the user explicitly asks for Phase 2/MVP work or a task naturally references Phase 2 modules from DOCUMENT/phase2_guide.md.
---

## Project-awareness rule
Read the relevant project context before acting:
- `CLAUDE.md`
- `.claude/project/overview.md`
- `.claude/project/phases.md`
- `.claude/project/layers.md`
- `.claude/project/phase2-scope.md`
- `.claude/project/current-state.md`
- `DOCUMENT/phase2_guide.md` for detailed file roles and ordering

# Purpose
Execute Phase 2 MVP work without drifting into Phase 3 production architecture.

## Phase 2 includes
- CMS v2.0 extension
- journal quality checks from MJL, SCImago, DOAJ, Beall/hijack evidence
- author and affiliation verification through ORCID, ROR, and Vietnamese-name matching
- Redis DOI cache and Celery background processing where needed
- LangGraph-style fan-out/fan-in orchestration
- aggregator and decision v2 using grounded sub-scores
- WORM audit log and reviewer queue endpoints
- Alembic migrations, metrics, tracing, snapshot scripts, tests, and eval

## Do not expand into
- frontend/dashboard unless explicitly requested
- appeals and reports
- full integrity detection beyond retraction evidence
- Kubernetes, CI/CD gates, production compliance, or self-hosted LLM infrastructure

## Procedure
1. Confirm the request is Phase 2 and not Phase 1 maintenance or Phase 3 production work.
2. Read the current files; many Phase 2 paths may still be placeholders.
3. Choose the smallest useful slice from the Phase 2 dependency order.
4. Implement deterministic schemas/connectors/snapshots before agent or LLM behavior.
5. Keep every decision grounded in source evidence and route uncertainty to `REVIEW`.
6. Add focused tests for changed behavior.
7. Run focused verification and update `.claude/project/current-state.md` after major milestones.

## Suggested implementation order
1. infrastructure/config/env/docker dependencies
2. schemas and CMS v2.0
3. connectors and snapshots
4. cache, audit, and author-name utilities
5. runtime agents and orchestration
6. database models/migrations
7. tasks, observability, API endpoints
8. scripts, tests, eval dataset

## Verification checklist
- Does the task fit Phase 2 and avoid Phase 3 creep?
- Did the code verify current file contents instead of trusting placeholders?
- Is every generated decision based on grounded evidence?
- Are weak/missing/conflicting signals routed to `REVIEW`?
- Are tests/checks appropriate for the changed slice?
