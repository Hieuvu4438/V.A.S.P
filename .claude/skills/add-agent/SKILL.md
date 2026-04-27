---
name: add-agent
description: Use when creating or refining an agent in ReviewAgent PTIT. The skill is aware of the full multi-layer roadmap, but by default constrains implementation to the current Phase 1 agent slice unless later-phase work is explicitly requested.
when_to_use: Use when the task touches files under src/reviewagent/agents, src/reviewagent/llm, or asks to create/refine Claude helper agents under .claude/agents.
---

## Project-awareness rule
Before implementing, distinguish between:
- full architecture context in `CLAUDE.md`
- architecture layers in `.claude/project/layers.md`
- delivery phases in `.claude/project/phases.md`
- roadmap context in `.claude/project/roadmap.md`
- active implementation scope in `.claude/project/phase1-scope.md`
- current repo state in `.claude/project/current-state.md`
- prompt and runtime-agent principles in `.claude/project/agent-design-reference.md`

# Purpose

Create or refine agents without confusing Claude Code helper agents with ReviewAgent runtime application agents.

## Two kinds of agents

### Claude Code helper agents
- Location: `.claude/agents/*.md`
- Purpose: help Claude Code perform development workflows.
- These are not runtime product features.

### ReviewAgent runtime application agents
- Location: `src/reviewagent/agents/`
- Purpose: application logic and AI-assisted verification inside the product.
- These must follow Phase 1 scope unless the user explicitly requests later-phase implementation.

## Phase 1 runtime agent types
- metadata agent
- decision agent
- sequential graph/state logic or equivalent pipeline

## Reference-only runtime agents by default
The design memo describes these production agents, but they are future scope unless explicitly requested:
- input router agent
- journal agent
- author agent
- integrity agent
- appeal agent

## Rules
- inspect actual files before assuming `BaseAgent`, graph orchestration, or prompt infrastructure exists
- use deterministic logic before model judgment
- consume schema-backed inputs
- default to safe behavior when evidence is weak
- keep orchestration sequential unless explicitly asked otherwise
- use structured/schema-backed outputs rather than free-text JSON
- do not invent metadata, DOI, ISSN, year, quartile, or indexing data

## Procedure
1. Determine whether the requested agent is a Claude Code helper agent or runtime ReviewAgent application agent.
2. Read the relevant `.claude/project` files listed above.
3. Read the target agent and neighboring files.
4. Read the relevant schemas and LLM prompt/gateway files.
5. Trace what the agent receives and what it must return.
6. Implement the narrowest logic that satisfies the current step.
7. Add tests for success and degraded paths when runtime behavior changes.

## Files to inspect first for runtime agents
- `src/reviewagent/agents/state.py`
- `src/reviewagent/agents/metadata_agent.py`
- `src/reviewagent/agents/decision_agent.py`
- `src/reviewagent/agents/graph.py`
- `src/reviewagent/llm/`
- `src/reviewagent/schemas/*.py`

## Verification checklist
- Is this a helper agent or a runtime product agent?
- Does the runtime agent only use grounded data?
- Does it stay in Phase 1 scope unless explicitly requested otherwise?
- Does it fail safe when evidence is incomplete?
- Is the returned structure aligned with current schemas?
