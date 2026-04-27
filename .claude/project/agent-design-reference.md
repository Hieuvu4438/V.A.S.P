# Agent design reference

This file distills `.claude/reviewagent-agent-design.md` into operational guidance for Claude Code. The design memo remains the long-form reference, but it is broader than the current Phase 1 codebase.

## Core prompt principles
- Constraint > capability: prompts should define what the agent must not do, especially around hallucinated metadata.
- Structured output is a contract: use tool use or schema-backed outputs rather than parsing free-text JSON.
- Context window is scarce: keep prompts compact, inject only relevant evidence, and reserve few-shot examples for edge cases.
- Grounded > generative: DOI, ISSN, quartile, year, indexing, and publication metadata must come from tool/API evidence, not memory.
- Deterministic before stochastic: validation, normalization, lookup, and scoring rules should be code-first where possible.

## Production runtime agents in the design memo
The long-form design describes seven runtime ReviewAgent application agents:

1. Input Router Agent — classify submission path and detect prompt injection.
2. Metadata Agent — fetch and reconcile metadata from Crossref/OpenAlex and related sources.
3. Journal Agent — verify journal quality, indexing, quartile, and predatory/hijack risks.
4. Author Agent — perform author and affiliation verification, including Vietnamese-name disambiguation.
5. Integrity Agent — identify content-integrity signals.
6. Decision Agent — make grounded APPROVE/REVIEW/REJECT decisions from evidence.
7. Appeal Agent — handle contested decisions with expanded evidence review.

## Active Phase 1 subset
Phase 1 should only activate the minimum subset needed for the PoC:
- Metadata Agent
- Decision Agent
- simple sequential orchestration or equivalent pipeline

The Router, Journal, Author, Integrity, and Appeal agents are roadmap/reference by default unless the user explicitly asks for later-phase implementation.

## Prompt structure guidance
Production prompts may use clear XML-style sections such as:
- `<role>`
- `<context>`
- `<workflow>`
- `<constraints>`
- `<output>`
- `<examples>`
- `<safety>`

For Phase 1, keep prompts shorter than the production design unless the added detail is necessary for the current task.

## Tool and output guidance
- Tool descriptions should say when to call the tool and when not to call it.
- Tool schemas should be treated as versioned contracts.
- Runtime application agents should return schema-backed output validated by server-side Pydantic models.
- Do not introduce the full production tool ecosystem unless the implementation phase requires it.

## Scope warning
Do not automatically implement all content from `.claude/reviewagent-agent-design.md`. In particular, avoid adding the full 7-agent runtime system, few-shot repository, prompt versioning/A-B testing, Langfuse integration, Reflexion lessons, appeal workflow, or production observability unless the user explicitly requests that scope.
