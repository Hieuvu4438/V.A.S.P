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
- implemented base / maintenance scope

### Phase 2 — MVP
- active setup for explicit Phase 2 work
- richer source coverage: journal, author/affiliation, and retraction evidence
- more complete agent orchestration with LangGraph-style fan-out/fan-in
- reviewer workflows, WORM audit, and operational support

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
The active implementation setup is now **Phase 2 MVP** when the user explicitly asks for Phase 2 work. The repository still contains Phase 1 PoC implementation as the base, so verify current files before assuming Phase 2 modules are implemented. Ambiguous maintenance requests should still be classified against the requested phase before coding.

## Design reference
`.claude/reviewagent-agent-design.md` is a long-form design memo for production-grade context, prompts, tools, skills, and runtime agents. Use its principles as reference, but do not treat all production agents or tool ecosystems in that memo as active implementation scope.

## Desired Phase 2 outcome
A usable internal MVP should support:
1. receive DOI plus claimed author/affiliation
2. fetch or reuse cached metadata
3. run metadata, journal, and author verification with grounded evidence
4. aggregate sub-scores and produce a fail-safe decision
5. persist decision, review state, and WORM audit log
6. expose submission/decision/reviewer APIs
7. evaluate with Phase 2 tests and gold dataset
