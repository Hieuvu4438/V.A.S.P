# Project overview

ReviewAgent PTIT is an AI-assisted system for verifying scientific publication submissions at PTIT.

## Product goal
The system helps verify publication claims against authoritative metadata sources and returns a structured decision with supporting evidence, auditability, and human review when needed.

## Full project shape
The broader project is designed as a verification platform with five functional layers:
1. identity and source verification
2. journal quality checks
3. author and affiliation verification
4. content integrity checks
5. final decisioning with human-in-the-loop review

These are architecture layers, not delivery phases.

## Delivery roadmap
The current roadmap has three delivery phases:

### Phase 1 — PoC
- backend only
- AI + API + DB + tests
- focus on DOI -> metadata -> CMS -> decision
- active implementation target in this repo

### Phase 2 — MVP
- broader source coverage
- more complete agent orchestration
- reviewer workflows and dashboard support
- stronger auditability and operational support

### Phase 3 — Production
- integrity checks
- appeal workflows
- multi-provider and self-hosted model strategy
- production-grade deployment, monitoring, and compliance features

## Main domain ideas
- A submission is usually driven by a DOI.
- Metadata should be fetched from authoritative services.
- Crossref is the primary metadata source in the PoC.
- OpenAlex is the fallback source in the PoC.
- Internal processing should normalize metadata into a canonical schema.
- Decisions must be based on grounded evidence, not model memory.
- Human review is part of the long-term system design, not an afterthought.

## Current delivery target
The active implementation target in this repo is still **Phase 1 PoC**. Claude should understand the whole roadmap, but when a request is ambiguous it should default to Phase 1 scope unless the user explicitly asks for MVP or Production work.

## Design reference
`.claude/reviewagent-agent-design.md` is a long-form design memo for production-grade context, prompts, tools, skills, and runtime agents. Use its principles as reference, but do not treat all production agents or tool ecosystems in that memo as active implementation scope.

## Desired PoC outcome
A minimal flow should work end-to-end:
1. receive a submission
2. validate DOI
3. fetch metadata
4. normalize into CMS
5. produce a decision
6. store result
7. expose result via API
8. evaluate with tests and scripts
