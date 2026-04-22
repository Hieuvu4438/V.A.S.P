---
name: phase1-backend-implementation
description: Use when implementing or modifying ReviewAgent PTIT features that belong to the current Phase 1 PoC slice. This skill understands the broader roadmap but constrains coding to the active DOI -> metadata -> CMS -> decision -> DB/API/test flow.
when_to_use: Use for coding tasks in this repo when the request should stay inside the current PoC scope and must avoid drifting into MVP or Production implementation work.
---

## Project-awareness rule
This skill should understand the broader project roadmap before acting:
- full project context: `CLAUDE.md`
- roadmap: `.claude/project/roadmap.md`
- current implementation slice: `.claude/project/phase1-scope.md`

# Purpose

This skill keeps implementation work aligned with the current project phase.

## Phase 1 PoC includes
- submission input with DOI
- Crossref metadata fetch
- OpenAlex fallback
- canonical metadata normalization
- decision generation from grounded evidence
- database persistence
- FastAPI endpoints
- tests and eval

## Do not expand into
- frontend
- reviewer workflows
- ORCID or author disambiguation
- journal quality snapshots
- integrity detection
- production infra and observability

## Procedure
1. Read the relevant files and `CLAUDE.md`.
2. Confirm the requested change belongs to Phase 1.
3. Identify the smallest set of files to edit.
4. Implement grounded, minimal logic.
5. Add or update tests.
6. Verify the result without broadening scope.

## Files to inspect first
- `CLAUDE.md`
- `.claude/project/phase1-scope.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase1_poc_backend_ai_step_by_step_prompts.md`

## Verification checklist
- Is the change inside Phase 1 scope?
- Does it preserve grounding before generation?
- Does it avoid new MVP/Production complexity?
- Are tests updated if behavior changed?
