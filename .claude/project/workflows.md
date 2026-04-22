# Common implementation workflows

## Add or refine a schema
1. Read the existing schema file.
2. Keep only the fields required by Phase 1.
3. Add validation only where it helps at system boundaries.
4. Ensure API and DB layers stay aligned.
5. Add unit tests for new validation behavior.

## Add or refine a connector
1. Read `config.py`, the base connector, and the target connector.
2. Keep the connector focused on fetch + parse + normalize.
3. Map authoritative response fields into the internal schema.
4. Handle misses as normal control flow where appropriate.
5. Add unit tests for parsing and miss cases.

## Add or refine an agent
1. Confirm the agent belongs in Phase 1 scope.
2. Keep logic grounded in schema-backed inputs.
3. Use deterministic rules before LLM judgment.
4. Fail safe when evidence is incomplete.
5. Add tests for success and degraded paths.

## Add or refine an API endpoint
1. Read request/response schemas first.
2. Keep the route thin and move logic to services/agents/repos.
3. Return structured responses.
4. Do not add unrelated auth or workflow complexity in PoC.
5. Add integration tests.

## Validate work
- run the relevant tests
- check the API path you changed
- confirm the implementation still fits Phase 1 only
