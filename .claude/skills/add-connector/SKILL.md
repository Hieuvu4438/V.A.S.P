---
name: add-connector
description: Use when creating or updating a connector in ReviewAgent PTIT. The skill knows the project has a larger roadmap, but defaults to the current authoritative metadata connector work unless the user explicitly asks for later-phase sources.
when_to_use: Use when the task involves an external source, HTTP fetching, parsing responses, mapping authoritative fields, or adding connector tests.
---

## Project-awareness rule
Read these first when scope is ambiguous:
- `CLAUDE.md`
- `.claude/project/roadmap.md`
- `.claude/project/phase1-scope.md`

# Purpose

Add or refine a connector without over-designing it.

## Phase 1 connector rules
- authoritative data first
- connector scope is fetch, parse, normalize
- misses should be handled explicitly
- provenance should be preserved

## Procedure
1. Read `src/reviewagent/config.py`.
2. Read `src/reviewagent/connectors/base.py`.
3. Read the target connector file.
4. Identify the minimum fields needed by the CMS.
5. Implement fetch + parse + mapping.
6. Ensure the output is compatible with current schemas.
7. Add focused unit tests.

## Files to inspect first
- `src/reviewagent/connectors/base.py`
- `src/reviewagent/schemas/cms.py`
- `src/reviewagent/connectors/crossref.py`
- `src/reviewagent/connectors/openalex.py`
- `tests/unit/`

## Verification checklist
- Does the connector return authoritative metadata only?
- Are misses treated safely?
- Is provenance attached or preserved?
- Are parsing tests present for at least one success case and one miss/failure case?
