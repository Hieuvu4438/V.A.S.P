---
name: update-project-context
description: Use when updating .claude/project context after major ReviewAgent PTIT decisions, milestones, scope changes, or implementation progress. Keeps Claude/Codex project understanding concise and current.
when_to_use: Use when the user asks to update project memory/context/docs, after significant implementation milestones, or when .claude/project needs to reflect a changed roadmap, phase boundary, or current repo state.
---

# Update Project Context

## Purpose

Keep `.claude/project` as the durable project-understanding layer for Claude Code and other coding assistants.

## Rules
- Keep context concise and operational.
- Do not copy full planning documents into `.claude/project`.
- Preserve the distinction between five architecture layers and three delivery phases.
- Default current implementation context to Phase 1 unless the project has explicitly moved forward.
- Update `.claude/project/current-state.md` after major implementation milestones.
- Update `.claude/project/phases.md` or `.claude/project/roadmap.md` only for real roadmap decisions, not temporary task plans.
- Treat `.claude/reviewagent-agent-design.md` as a design memo/reference, not a source to copy wholesale.

## Procedure
1. Read `CLAUDE.md`.
2. Read the relevant `.claude/project/*.md` files.
3. Read the source document or implementation change that triggered the context update.
4. Identify the smallest context file set that needs editing.
5. Update concise facts, rules, or scope boundaries.
6. Remove or revise stale context if the repo state has changed.
7. Verify that no new context implies broader implementation scope than intended.

## Files commonly updated
- `.claude/project/overview.md`
- `.claude/project/architecture.md`
- `.claude/project/roadmap.md`
- `.claude/project/phases.md`
- `.claude/project/layers.md`
- `.claude/project/phase1-scope.md`
- `.claude/project/current-state.md`
- `.claude/project/agent-design-reference.md`
- `.claude/project/workflows.md`

## Verification checklist
- Is the context still short enough to scan?
- Is the current phase clear?
- Are future-phase items marked as future/reference unless explicitly active?
- Does the context match actual repo state?
- Did the update avoid duplicating source documents?
