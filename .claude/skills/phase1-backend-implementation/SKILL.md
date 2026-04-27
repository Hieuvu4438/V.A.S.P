---
name: phase1-backend-implementation
description: Use when implementing or modifying ReviewAgent PTIT features that belong to the current Phase 1 PoC slice. This skill understands the broader roadmap but constrains coding to the active DOI -> metadata -> CMS -> decision -> DB/API/test flow.
when_to_use: Use for coding tasks in this repo when the request should stay inside the current PoC scope and must avoid drifting into MVP or Production implementation work.
---

## Project-awareness rule
This skill should understand the broader project roadmap before acting:
- full project context: `CLAUDE.md`
- roadmap: `.claude/project/roadmap.md`
- phases: `.claude/project/phases.md`
- layers: `.claude/project/layers.md`
- current implementation slice: `.claude/project/phase1-scope.md`
- current repo state: `.claude/project/current-state.md`

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

## Placeholder rule
Many files in the repo may exist as scaffolding. File existence does not mean a pattern is implemented. Read the target files first, and when a placeholder must be filled, implement only the minimal Phase 1 behavior required by the task.

## Procedure
1. Read the relevant files and `CLAUDE.md`.
2. Read `.claude/project/current-state.md`.
3. Confirm the requested change belongs to Phase 1.
4. Identify the smallest set of files to edit.
5. Implement grounded, minimal logic.
6. Add or update tests.
7. Verify the result without broadening scope.

## Files to inspect first
- `CLAUDE.md`
- `.claude/project/phase1-scope.md`
- `.claude/project/current-state.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase1_poc_backend_ai_step_by_step_prompts.md`

## Verification checklist
- Is the change inside Phase 1 scope?
- Does it preserve grounding before generation?
- Does it avoid new MVP/Production complexity?
- Did the implementation avoid treating placeholders as completed systems?
- Are tests updated if behavior changed?
