---
name: add-agent
description: Use when creating or refining an agent in ReviewAgent PTIT. The skill is aware of the full multi-layer roadmap and distinguishes Phase 1 maintenance, Phase 2 MVP agent work, and Phase 3 production scope.
when_to_use: Use when the task touches files under src/reviewagent/agents, src/reviewagent/llm, or asks to create/refine Claude helper agents under .claude/agents.
---

## Project-awareness rule
Before implementing, distinguish between:
- full architecture context in `CLAUDE.md`
- architecture layers in `.claude/project/layers.md`
- delivery phases in `.claude/project/phases.md`
- roadmap context in `.claude/project/roadmap.md`
- active Phase 1 implementation scope in `.claude/project/phase1-scope.md`
- active Phase 2 MVP scope in `.claude/project/phase2-scope.md`
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
- These must follow the requested phase scope: Phase 1 maintenance, Phase 2 MVP, or explicit Phase 3 work.

## Phase 1 runtime agent types
- metadata agent
- decision agent
- sequential graph/state logic or equivalent pipeline

## Phase 2 runtime agent types
- input/router agent
- metadata agent with cache/source evidence
- journal agent
- author agent
- aggregator agent
- decision agent v2
- LangGraph-style fan-out/fan-in orchestration

## Phase 3/reference-only runtime agents by default
The design memo describes production agents and infrastructure, but these remain Phase 3 unless explicitly requested:
- appeal agent

## Rules
- inspect actual files before assuming `BaseAgent`, graph orchestration, or prompt infrastructure exists
- use deterministic logic before model judgment
- consume schema-backed inputs
- default to safe behavior when evidence is weak
- keep orchestration sequential for Phase 1; use LangGraph-style fan-out/fan-in only for explicit Phase 2 work
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
- Does it stay in the requested phase scope?
- Does it fail safe when evidence is incomplete?
- Is the returned structure aligned with current schemas?
