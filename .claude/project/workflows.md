# Common implementation workflows

## First step for every workflow
1. Read `CLAUDE.md` and the directly relevant `.claude/project` files.
2. Inspect the actual target files before assuming a pattern exists.
3. Check `.claude/project/current-state.md` when deciding whether a module is implemented or only placeholder scaffolding.
4. Classify the request as Phase 1 maintenance, Phase 2 MVP work, Phase 3 production work, or design-only before coding.
5. Use `.claude/project/phase2-scope.md` and `DOCUMENT/phase2_guide.md` when the user explicitly asks for Phase 2/MVP work.

## Add or refine a schema
1. Read the existing schema file.
2. Confirm whether the schema change is Phase 1 base maintenance or Phase 2 CMS v2.0 work.
3. Add validation only where it helps at system boundaries.
4. Ensure API and DB layers stay aligned.
5. Add unit tests for new validation behavior.

## Add or refine a connector
1. Read `config.py`, the target connector, and any existing connector base if it has real content.
2. Do not assume `BaseConnector` or shared connector utilities exist before reading them.
3. Keep the connector focused on fetch + parse + normalize.
4. Map authoritative response fields into internal schemas with provenance.
5. Handle misses as normal control flow where appropriate.
6. Add unit tests for parsing and miss cases.

## Add or refine an agent
1. Confirm the agent belongs to the requested phase.
2. Read the target agent, neighboring files, schemas, and LLM prompt/gateway files.
3. Do not assume `BaseAgent`, LangGraph orchestration, or prompt infrastructure exists before reading it.
4. Keep logic grounded in schema-backed inputs.
5. Use deterministic rules before LLM judgment.
6. Fail safe when evidence is incomplete.
7. Add tests for success and degraded paths.

## Add Phase 2 journal or author verification
1. Read `.claude/project/phase2-scope.md` and the matching section in `DOCUMENT/phase2_guide.md`.
2. Implement schemas and deterministic matching before agent orchestration.
3. Use snapshots/connectors as evidence sources; never let the LLM invent indexing, quartile, ORCID, ROR, or affiliation facts.
4. Route absent or conflicting evidence to `REVIEW`.
5. Add focused tests for exact match, fuzzy/degraded match, and missing evidence.

## Add or refine an API endpoint
1. Read request/response schemas first.
2. Read the target router and dependency files before assuming FastAPI structure exists.
3. Keep the route thin and move logic to services/agents/repos when those layers exist.
4. Return structured responses.
5. For Phase 2 reviewer endpoints, write WORM audit entries for assignments and overrides.
6. Add integration tests.

## Validate work
- run the relevant tests
- check the API path you changed when applicable
- confirm the implementation still fits the requested phase
- verify that no placeholder module was treated as a completed feature
