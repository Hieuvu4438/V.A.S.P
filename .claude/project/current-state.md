# Current repository state

This file is a lightweight context snapshot for Claude Code. Verify current files before relying on it, and update it after major implementation milestones.

## Observed implementation state
The repository is currently in an early Phase 1 PoC state.

Real implemented areas include:
- `src/reviewagent/config.py` — application, database, API, and LLM settings.
- `src/reviewagent/schemas/submission.py` — submission request/response schemas and DOI normalization.
- `src/reviewagent/schemas/cms.py` — canonical metadata schema with DOI, provenance, journal, author, and publication date validation.
- `src/reviewagent/schemas/decision.py` — structured decision output with confidence, rationale, flags, and sub-scores.
- `tests/unit/test_schemas.py` — unit coverage for schema behavior.

Many Phase 1 or future-phase paths may exist as placeholder scaffolding. Before assuming behavior exists, inspect the file contents.

Likely placeholder-only areas until verified:
- `src/reviewagent/agents/`
- `src/reviewagent/connectors/`
- `src/reviewagent/api/`
- `src/reviewagent/db/`
- `src/reviewagent/llm/`
- `src/reviewagent/snapshots/`
- `src/reviewagent/tasks/`
- `src/reviewagent/observability/`
- `scripts/eval.py`

## Practical implications
- Do not assume `BaseAgent`, `BaseConnector`, graph orchestration, LLM gateway, FastAPI routers, DB repositories, or eval harnesses already exist.
- Do not treat placeholder files as completed architecture.
- When implementing into an empty placeholder file, build only the minimal Phase 1 version required by the user request.
- Prefer schema-backed contracts and focused tests before broad orchestration.

## Phase 1 anchor
Current implementation should progress toward:
`DOI submission -> Crossref -> OpenAlex fallback -> CMS -> decision -> DB/API -> tests/eval`.
