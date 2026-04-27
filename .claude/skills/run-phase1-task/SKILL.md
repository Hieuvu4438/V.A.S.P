---
name: run-phase1-task
description: Use as a general-purpose playbook for executing a ReviewAgent PTIT task when the requested implementation belongs to the current Phase 1 PoC slice. The skill is aware of the broader roadmap and uses it to avoid confusion, but constrains execution to current scope.
when_to_use: Use when a task does not fit a narrower project skill but still belongs to the current PoC backend+AI phase.
---

## Project-awareness rule
Use all layers of context:
- `CLAUDE.md` for the whole project
- `.claude/project/roadmap.md` for roadmap context
- `.claude/project/phases.md` for delivery phase boundaries
- `.claude/project/layers.md` for the five architecture layers
- `.claude/project/phase1-scope.md` for current implementation limits
- `.claude/project/current-state.md` for actual repo maturity

# Purpose

Provide a standard way to execute PoC tasks consistently.

## Procedure
1. Read `CLAUDE.md` and confirm the task belongs to Phase 1.
2. If scope is ambiguous, classify the request against `.claude/project/layers.md` and `.claude/project/phases.md`.
3. If the task touches Layers 2, 3, 4, reviewer workflows, appeals, or production operations, clarify whether the user wants future-phase work or only design/context updates.
4. Read the directly relevant files.
5. Identify the minimum file set to change.
6. Implement only the requested behavior.
7. Add or update tests.
8. Run focused verification.
9. Summarize what changed and what remains out of scope.

## Scope guardrails
- no frontend
- no reviewer operations
- no advanced journal/author/integrity systems
- no production infra expansion
- no broad abstractions for placeholder modules

## Suggested references
- `DOCUMENT/implementation_plan.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase1_poc_backend_ai_step_by_step_prompts.md`

## Verification checklist
- Is the task still within the PoC backend+AI scope?
- Did the implementation avoid unnecessary abstractions?
- Were tests or checks run for the changed area?
- Did the final state stay grounded and fail-safe?
- Did the work avoid confusing architecture layers with delivery phases?
