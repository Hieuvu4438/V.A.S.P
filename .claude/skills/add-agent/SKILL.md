---
name: add-agent
description: Use when creating or refining an agent in ReviewAgent PTIT. The skill is aware of the full multi-layer roadmap, but by default constrains implementation to the current Phase 1 agent slice unless later-phase work is explicitly requested.
when_to_use: Use when the task touches files under src/reviewagent/agents and needs grounded business logic or orchestration changes.
---

## Project-awareness rule
Before implementing, distinguish between:
- full architecture context in `CLAUDE.md`
- roadmap context in `.claude/project/roadmap.md`
- active implementation scope in `.claude/project/phase1-scope.md`

# Purpose

Implement Phase 1 agents with grounded inputs and minimal orchestration.

## Phase 1 agent types
- metadata agent
- decision agent
- sequential graph/state logic

## Rules
- use deterministic logic before model judgment
- consume schema-backed inputs
- default to safe behavior when evidence is weak
- keep orchestration sequential unless explicitly asked otherwise

## Procedure
1. Read the target agent and neighboring agent files.
2. Read the relevant schemas.
3. Trace what the agent receives and what it must return.
4. Implement the narrowest logic that satisfies the current step.
5. Add tests for success and degraded paths.

## Files to inspect first
- `src/reviewagent/agents/state.py`
- `src/reviewagent/agents/metadata_agent.py`
- `src/reviewagent/agents/decision_agent.py`
- `src/reviewagent/agents/graph.py`
- `src/reviewagent/schemas/*.py`

## Verification checklist
- Does the agent only use grounded data?
- Does it stay in Phase 1 scope?
- Does it fail safe when evidence is incomplete?
- Is the returned structure aligned with current schemas?
