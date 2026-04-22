---
name: run-phase1-task
description: Use as a general-purpose playbook for executing a ReviewAgent PTIT task when the requested implementation belongs to the current Phase 1 PoC slice. The skill is aware of the broader roadmap and uses it to avoid confusion, but constrains execution to current scope.
when_to_use: Use when a task does not fit a narrower project skill but still belongs to the current PoC backend+AI phase.
---

## Project-awareness rule
Use all three layers of context:
- `CLAUDE.md` for the whole project
- `.claude/project/roadmap.md` for roadmap context
- `.claude/project/phase1-scope.md` for current implementation limits

# Purpose

Provide a standard way to execute PoC tasks consistently.

## Procedure
1. Read `CLAUDE.md` and confirm the task belongs to Phase 1.
2. Read the directly relevant files.
3. Identify the minimum file set to change.
4. Implement only the requested behavior.
5. Add or update tests.
6. Run focused verification.
7. Summarize what changed and what remains out of scope.

## Scope guardrails
- no frontend
- no reviewer operations
- no advanced journal/author/integrity systems
- no production infra expansion

## Suggested references
- `DOCUMENT/implementation_plan.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase1_poc_backend_ai_step_by_step_prompts.md`

## Verification checklist
- Is the task still within the PoC backend+AI scope?
- Did the implementation avoid unnecessary abstractions?
- Were tests or checks run for the changed area?
- Did the final state stay grounded and fail-safe?
