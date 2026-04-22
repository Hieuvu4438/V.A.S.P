# Project architecture

## Full architecture model
The project is designed around five functional layers:
1. identity and source verification
2. journal quality checks
3. author and affiliation verification
4. content integrity checks
5. decisioning and human-in-the-loop workflow

## Phase 1 PoC architecture
The current implementation slice is a simplified subset of the full architecture.

### Target PoC pipeline
`POST /submissions` -> validate input -> fetch metadata -> normalize CMS -> decision -> save DB -> return response

## Main code areas
- `src/reviewagent/schemas/` — Pydantic models for submission, CMS, decision
- `src/reviewagent/connectors/` — external metadata fetchers
- `src/reviewagent/agents/` — orchestration and business logic
- `src/reviewagent/llm/` — prompt and model gateway for decisioning
- `src/reviewagent/db/` — persistence layer
- `src/reviewagent/api/` — FastAPI app and routes
- `tests/` — validation of PoC behavior

## Phase 1 data flow
1. submission request enters API
2. input schema validates DOI and request payload
3. metadata agent queries Crossref
4. if Crossref does not return usable metadata, query OpenAlex
5. normalize response into Canonical Metadata Schema
6. decision agent evaluates grounded evidence
7. store submission, publication, and decision
8. expose decision via API

## How later phases extend this
- add richer journal quality verification
- add author identity and affiliation checks
- add integrity signals
- add reviewer workflow and appeals
- add more operational and compliance layers

## Core technical rules
- Prefer exact validation and explicit mappings over implicit inference.
- The CMS should carry provenance like source API and fetch time.
- The decision layer must not invent metadata.
- If sources are missing or inconsistent, the safe default is `REVIEW`.

## Not part of the current implementation slice
- parallel multi-agent orchestration
- ORCID and author identity matching
- journal ranking or predatory journal snapshots
- integrity detectors
- reviewer operations and appeals
- production observability stack
