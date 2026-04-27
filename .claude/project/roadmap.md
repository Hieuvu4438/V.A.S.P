# Project roadmap

This file summarizes the broader ReviewAgent PTIT roadmap so Claude understands the full project, not just the currently active implementation slice.

## Product direction
ReviewAgent PTIT is intended to evolve from a narrow PoC into a full publication-verification platform with grounded metadata, layered verification, policy-aware decisioning, human review, auditability, and operational maturity.

## Delivery phases
The project has three delivery phases. The five items in `.claude/project/architecture.md` are architecture layers, not five delivery phases.

## Phase 1 — PoC
### Goal
Prove the minimal backend + AI flow works end-to-end.

### Main focus
- submission with DOI
- Crossref metadata fetch
- OpenAlex fallback
- CMS normalization
- grounded decision generation
- DB persistence
- FastAPI endpoints
- tests and evaluation

### Main exclusions
- frontend
- reviewer workflows
- advanced journal checks
- author identity workflows
- integrity detection
- production infra

## Phase 2 — MVP
### Goal
Expand the PoC into a usable internal system with broader verification coverage and reviewer support.

### Likely additions
- richer source coverage such as DOAJ, SCImago, MJL, Retraction Watch
- broader multi-agent orchestration
- reviewer-facing operations and queue handling
- audit logging improvements
- stronger deployment and operational setup
- more complete workflow coverage around decisions

## Phase 3 — Production
### Goal
Operate the system reliably at scale with compliance, observability, advanced detection, and appeal handling.

### Likely additions
- integrity signal pipelines
- appeal workflow
- self-hosted and multi-provider model strategy
- production observability and reliability patterns
- compliance and governance features
- stronger deployment architecture and rollout strategy

## Architecture layer to phase mapping

| Architecture layer | Phase 1 — PoC | Phase 2 — MVP | Phase 3 — Production |
|---|---|---|---|
| Identity and source verification | DOI, Crossref, OpenAlex, CMS provenance | broader sources and stronger source coverage | hardened source governance and reliability |
| Journal quality checks | out of scope | MJL, SCImago, DOAJ, blacklist/hijack checks | production snapshots and operational governance |
| Author and affiliation verification | out of scope | ORCID, ROR, affiliation and Vietnamese-name matching | stronger identity workflows and review tooling |
| Content integrity checks | out of scope | possible initial retraction/integrity signals | full integrity pipelines and escalation workflows |
| Decisioning and HITL | simple grounded decision | reviewer workflow and richer audit log | appeals, compliance, audit, and operations |

## How to use roadmap context
- Use this file when the user asks about the whole project, future direction, or architecture beyond the current PoC.
- Use `.claude/project/phase1-scope.md` when the user asks to implement something in the current repo scope.
- If the user request is ambiguous, understand the full roadmap first, then constrain implementation to the currently requested phase.
