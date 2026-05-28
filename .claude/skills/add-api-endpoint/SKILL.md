---
name: add-api-endpoint
description: Use when adding or refining FastAPI endpoints for ReviewAgent PTIT. The skill understands Phase 1 submission/decision APIs and Phase 2 MVP reviewer/workflow APIs without drifting into Phase 3.
when_to_use: Use when a task touches src/reviewagent/api and should produce or change a request/response path.
---

## Project-awareness rule
Read these first when the endpoint scope is unclear:
- `CLAUDE.md`
- `.claude/project/roadmap.md`
- `.claude/project/phases.md`
- `.claude/project/phase1-scope.md`
- `.claude/project/phase2-scope.md`
- `.claude/project/current-state.md`

# Purpose

Add or update API endpoints without pulling in unrelated architecture.

## Endpoint types

### Phase 1 endpoint types
- create submission
- fetch decision
- health check

### Phase 2 endpoint types
- reviewer queue list/detail
- reviewer assignment
- manual decision override
- audit-aware workflow state updates

## Rules
- inspect `src/reviewagent/api/*` before assuming routers, deps, or app setup exist
- keep route handlers thin
- validate with schemas
- delegate logic to agents/repos/services when those layers exist
- return structured responses
- do not add appeals, reports, production auth, or unrelated workflow complexity unless explicitly requested
- for Phase 2 reviewer endpoints, include audit behavior for assignments and manual overrides

## Procedure
1. Read request and response schemas first.
2. Read `.claude/project/current-state.md` to avoid assuming placeholder API files are implemented.
3. Read the target router and `api/deps.py` if they exist and have real content.
4. Identify the service/agent/repository calls needed.
5. Implement the smallest route change that works.
6. Add or update integration tests.

## Files to inspect first
- `src/reviewagent/api/main.py`
- `src/reviewagent/api/deps.py`
- `src/reviewagent/api/routers/submissions.py`
- `src/reviewagent/api/routers/decisions.py`
- `src/reviewagent/api/routers/health.py`
- `src/reviewagent/schemas/*.py`

## Verification checklist
- Is the response schema-backed?
- Is the route inside the requested phase scope?
- Is logic kept out of the router where possible?
- Did the implementation avoid assuming placeholder API files were complete?
- Are integration tests updated?
