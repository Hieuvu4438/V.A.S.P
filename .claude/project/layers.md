# Architecture layers

ReviewAgent PTIT has five functional architecture layers. These layers describe system responsibilities; they are not delivery phases.

## Layer 1 — Identity and source verification
- Responsibility: validate identifiers, fetch authoritative metadata, normalize source evidence, and preserve provenance.
- Current status: active-now.
- Phase mapping: Phase 1 implements the minimum DOI -> Crossref -> OpenAlex -> CMS slice.
- Repo signals: `src/reviewagent/schemas/`, `src/reviewagent/connectors/`, metadata agent work.
- Guardrail: metadata must come from authoritative source responses, not model memory.

## Layer 2 — Journal quality checks
- Responsibility: verify journal indexing, quartile, whitelist/blacklist status, hijack risk, and journal reputation.
- Current status: future-phase.
- Phase mapping: mostly Phase 2 MVP, hardened in Phase 3 Production.
- Repo signals: snapshot or journal connector placeholders may exist, but they are not active Phase 1 scope.
- Guardrail: do not add MJL, SCImago, DOAJ, Beall, Cabells, or hijack-check workflows unless explicitly requested.

## Layer 3 — Author and affiliation verification
- Responsibility: verify that the PTIT claimant is actually an author and that affiliation evidence is consistent.
- Current status: future-phase.
- Phase mapping: mostly Phase 2 MVP, strengthened in Phase 3 Production.
- Repo signals: ORCID/ROR/author-disambiguation concepts are roadmap context only unless requested.
- Guardrail: do not add ORCID, ROR, Vietnamese-name disambiguation, or affiliation matching to Phase 1 tasks by default.

## Layer 4 — Content integrity checks
- Responsibility: detect integrity signals such as retractions, tortured phrases, paper-mill patterns, or suspicious references.
- Current status: future-phase.
- Phase mapping: possible initial signals in Phase 2, full integrity pipelines in Phase 3.
- Repo signals: integrity-related placeholders or prompt designs are reference-only unless requested.
- Guardrail: do not add integrity detectors to Phase 1 implementation unless the user explicitly moves scope.

## Layer 5 — Decisioning and human-in-the-loop workflow
- Responsibility: produce structured decisions from grounded evidence and route uncertain cases to human review.
- Current status: active-now for minimal decisioning; future-phase for reviewer operations and appeals.
- Phase mapping: simple decision in Phase 1, reviewer workflow in Phase 2, appeals/audit/compliance in Phase 3.
- Repo signals: `src/reviewagent/schemas/decision.py`, decision agent, LLM prompt/gateway work.
- Guardrail: Phase 1 decisions should fail safe to `REVIEW`; do not build reviewer queues or appeals by default.

## Default interpretation rule
When a task references a layer without naming a delivery phase, classify the requested work first. If it touches Layers 2, 3, 4, or full HITL workflows, ask whether the user wants future-phase implementation or only design/context updates.
