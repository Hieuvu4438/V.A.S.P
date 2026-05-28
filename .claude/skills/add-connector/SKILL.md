---
name: add-connector
description: Use when creating or updating a connector in ReviewAgent PTIT. The skill understands Phase 1 metadata connectors and Phase 2 MVP journal/author/retraction evidence connectors.
when_to_use: Use when the task involves an external source, HTTP fetching, parsing responses, mapping authoritative fields, or adding connector tests.
---

## Project-awareness rule
Read these first when scope is ambiguous:
- `CLAUDE.md`
- `.claude/project/roadmap.md`
- `.claude/project/phases.md`
- `.claude/project/layers.md`
- `.claude/project/phase1-scope.md`
- `.claude/project/phase2-scope.md`
- `.claude/project/current-state.md`

# Purpose

Add or refine a connector without over-designing it or pulling Phase 3 source systems into Phase 1/2 work.

## Phase 1 active connectors
- Crossref primary metadata lookup
- OpenAlex fallback metadata lookup

## Phase 2 connector/evidence sources
These sources are in scope for explicit Phase 2/MVP work:
- DOAJ
- SCImago
- Master Journal List
- Retraction Watch
- ORCID
- ROR
- Beall/Cabells or other blacklist sources

## Connector rules
- authoritative data first
- connector scope is fetch, parse, normalize
- misses should be handled explicitly
- provenance should be preserved
- map only fields required by the current requested phase schemas
- do not invent metadata when an API response is missing or incomplete

## Procedure
1. Read `src/reviewagent/config.py`.
2. Read `.claude/project/current-state.md` to avoid assuming placeholder files are implemented.
3. Read `src/reviewagent/connectors/base.py` if it exists and has real content.
4. Read the target connector file.
5. Read `src/reviewagent/schemas/cms.py`.
6. Identify the minimum fields needed by the CMS.
7. Implement fetch + parse + mapping.
8. Ensure the output is compatible with current schemas.
9. Add focused unit tests with mocked HTTP responses.

## Files to inspect first
- `src/reviewagent/config.py`
- `src/reviewagent/connectors/base.py`
- `src/reviewagent/schemas/cms.py`
- `src/reviewagent/connectors/crossref.py`
- `src/reviewagent/connectors/openalex.py`
- `tests/unit/`

## Verification checklist
- Does the connector return authoritative metadata only?
- Are misses treated safely?
- Is provenance attached or preserved?
- Is the connector inside the requested phase scope?
- Are parsing tests present for at least one success case and one miss/failure case?
