# Project architecture

## Full five-layer architecture
ReviewAgent PTIT is designed around five functional architecture layers:

1. **Identity and source verification**
   - Validate publication identifiers and source metadata.
   - Use authoritative sources before model reasoning.
   - Phase 1 uses this layer through DOI, Crossref, OpenAlex, CMS, and provenance.

2. **Journal quality checks**
   - Verify journal indexing, quartile, whitelist/blacklist, hijack risk, and source reputation.
   - This is future-phase scope unless explicitly requested.

3. **Author and affiliation verification**
   - Verify that the PTIT claimant is actually an author of the publication.
   - Includes ORCID, affiliation normalization, and Vietnamese-name disambiguation.
   - This is future-phase scope unless explicitly requested.

4. **Content integrity checks**
   - Detect integrity signals such as retractions, tortured phrases, paper-mill patterns, or suspicious references.
   - This is future-phase scope unless explicitly requested.

5. **Decisioning and human-in-the-loop workflow**
   - Produce structured decisions from grounded evidence.
   - Route weak or conflicting evidence to review.
   - Phase 1 uses only a minimal decisioning slice; reviewer operations and appeals are later.

## Phase 1 PoC architecture
The current implementation slice is a simplified subset of the full architecture. It mostly exercises Layer 1 and a minimal part of Layer 5.

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
