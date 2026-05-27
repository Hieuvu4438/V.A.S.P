# Phase 2 MVP Backend + AI Full Pipeline — File Coding Plan

Tài liệu này mô tả **Phase 2 MVP** cho ReviewAgent PTIT ở phạm vi **backend + AI service + agents**, không bao gồm frontend/dashboard UI.

Mục tiêu của file này là trả lời rõ:

1. Phase 2 cần code những file nào.
2. Mỗi file sắp code có chức năng gì.
3. Mỗi task nên chia nhỏ ra sao.
4. Nên code theo thứ tự nào để dependency không bị rối.
5. Phase 2 kế thừa Phase 1 như thế nào.

Nguồn tham chiếu chính:

- `DOCUMENT/phase1_guide.md`
- `DOCUMENT/phase1_poc_backend_ai_file_matrix.md`
- `DOCUMENT/phase2_guide.md`
- `.claude/project/overview.md`
- `.claude/project/architecture.md`
- `.claude/project/phases.md`
- `.claude/project/layers.md`
- `.claude/project/current-state.md`

---

## 1. Scope quyết định

### Phase 2 được hiểu là gì?

Phase 2 là bước mở rộng từ Phase 1 PoC thành **MVP nội bộ**.

Phase 1 đã có luồng tối thiểu:

```text
POST /submissions
  -> validate DOI
  -> Crossref
  -> OpenAlex fallback
  -> CMS
  -> decision
  -> DB
  -> API response
```

Phase 2 mở rộng thành pipeline nhiều lớp hơn:

```text
POST /submissions
  -> validate DOI + claimed author + claimed affiliation
  -> Redis cache check
  -> metadata agent
  -> journal agent
  -> author agent
  -> aggregator agent
  -> decision agent v2
  -> save DB
  -> audit WORM log
  -> reviewer queue when needed
  -> API response / polling endpoints
```

### Có làm frontend không?

Không. File này chỉ bao gồm:

- backend FastAPI
- AI/LLM service
- agents
- connectors
- snapshots
- cache
- DB models/repositories
- Celery tasks
- audit log
- observability backend
- scripts
- tests/eval

Không bao gồm:

- frontend web app
- reviewer dashboard UI
- charts UI
- admin panel UI

### Có làm Phase 3 không?

Không. Các phần sau để Phase 3 hoặc chỉ làm rất nhỏ nếu cần cho MVP:

- appeal workflow đầy đủ
- reports/export nâng cao
- production Kubernetes
- multi-provider/self-hosted LLM strategy
- paper-mill/integrity detectors đầy đủ
- CI/CD production eval gate
- compliance governance đầy đủ

---

## 2. Phase 2 full backend + AI flow

```text
User submits:
  doi
  user_claimed_author
  user_claimed_affiliation

        |
        v

api/routers/submissions.py
  - validate request
  - create Submission(status=PROCESSING)
  - choose sync or async pipeline

        |
        v

cache/redis_client.py
  - check cms:{doi_hash}
  - cache hit: reuse CMS if fresh
  - cache miss: continue metadata fetch

        |
        v

agents/graph.py
  - build LangGraph pipeline
  - orchestrate metadata, journal, author, aggregator, decision

        |
        v

metadata_agent.py
  - Crossref first
  - OpenAlex fallback
  - Retraction Watch check can enrich CMS retraction fields
  - output CanonicalMetadataSchema v2.0

        |
        +------------------+
        |                  |
        v                  v

journal_agent.py       author_agent.py
  - MJL lookup           - ORCID verification
  - SCImago lookup       - ROR affiliation normalization
  - DOAJ lookup          - Vietnamese-name normalization
  - Beall check          - fuzzy/permutation name matching
  - hijack flag          - output AuthorCheckResult
  - output JournalCheckResult

        \                  /
         \                /
          v              v

aggregator_agent.py
  - collect CMS + journal + author + retraction evidence
  - compute sub-scores
  - build evidence_panel
  - collect machine-readable flags

        |
        v

decision_agent.py v2
  - deterministic score formula first
  - optional LLM CoVe verification
  - optional self-consistency k=3
  - calibrated confidence
  - APPROVE / REVIEW / REJECT

        |
        v

DB layer
  - submissions
  - publications
  - decisions
  - journal_checks
  - audit_log

        |
        v

audit/worm_logger.py
  - write submission.created
  - write decision.created
  - write review.overridden when reviewer decides
  - verify HMAC chain

        |
        v

API response
  - status
  - decision_id
  - decision
  - confidence
  - evidence_panel
  - review status if routed to human review
```

---

## 3. Main design principles for Phase 2

### 3.1. Keep Phase 1 behavior as baseline

Do not break the working Phase 1 path. A DOI-only request should still be able to run through metadata + decision, but Phase 2 request should support author and affiliation fields.

### 3.2. Grounding before generation

All factual metadata must come from:

- Crossref
- OpenAlex
- ORCID
- ROR
- DOAJ
- Retraction Watch
- offline snapshots such as MJL, SCImago, Beall/hijack list

LLM must not invent:

- DOI
- title
- authors
- ISSN
- journal index
- quartile
- ORCID
- affiliation
- retraction status

### 3.3. Deterministic before stochastic

Order of reasoning:

1. Validate input.
2. Fetch authoritative evidence.
3. Normalize into schemas.
4. Compute deterministic sub-scores.
5. Use LLM only for final grounded decision explanation and verification.

### 3.4. Fail safe

Missing or conflicting evidence should route to `REVIEW`, not optimistic `APPROVE`.

Examples:

- DOI not found in Crossref/OpenAlex -> `REVIEW` or failed metadata status depending API contract.
- Journal not indexed and no whitelist evidence -> `REVIEW`.
- Author name cannot be matched -> `REVIEW`.
- Predatory/hijacked/retracted evidence -> likely `REJECT`.

### 3.5. Backend-first, no frontend dependency

Reviewer queue is exposed as API endpoints only. Any UI can be added later, but Phase 2 backend should work with curl/Postman/API clients.

---

## 4. File groups and responsibilities

## 4.1. Foundation and configuration

### `pyproject.toml`

**Purpose:** Add Phase 2 dependencies.

**Code tasks:**

1. Add orchestration/runtime dependencies:
   - `langgraph`
   - `celery`
   - `redis`
2. Add backend/ops dependencies:
   - `alembic`
   - `prometheus-client`
3. Add optional AI/observability dependencies:
   - `langfuse`
4. Add test dependencies if missing:
   - `pytest-asyncio`
   - `respx` or equivalent HTTP mocking library
5. Keep Phase 1 dependencies intact.

**Why first:** Other Phase 2 files import these packages.

---

### `.env.example`

**Purpose:** Document all Phase 2 env vars.

**Code tasks:**

1. Keep Phase 1 variables:
   - `APP__*`
   - `DATABASE__URL`
   - `LLM__*`
2. Add Redis:
   - `REDIS__URL`
3. Add Celery:
   - `CELERY__BROKER_URL`
   - `CELERY__RESULT_BACKEND`
4. Add ORCID:
   - `ORCID__BASE_URL`
   - `ORCID__CLIENT_ID`
   - `ORCID__CLIENT_SECRET`
5. Add ROR/DOAJ/Retraction Watch base URLs.
6. Add snapshot paths:
   - `SNAPSHOT__MJL_PATH`
   - `SNAPSHOT__SCIMAGO_PATH`
   - `SNAPSHOT__BEALL_PATH`
   - `SNAPSHOT__HIJACK_PATH`
7. Add audit:
   - `AUDIT__SECRET_KEY`
8. Add thresholds:
   - `THRESHOLD__AUTO_APPROVE`
   - `THRESHOLD__AUTO_REJECT`
9. Add LLM v2 options:
   - `LLM__SELF_CONSISTENCY_K`
   - `LLM__COVE_ENABLED`
10. Add observability:
   - `LANGFUSE__PUBLIC_KEY`
   - `LANGFUSE__SECRET_KEY`
   - `LANGFUSE__HOST`
   - `OBSERVABILITY__METRICS_ENABLED`

---

### `src/reviewagent/config.py`

**Purpose:** Central typed settings for the whole backend.

**Code tasks:**

1. Keep existing Phase 1 settings classes.
2. Add `RedisSettings`.
3. Add `CelerySettings`.
4. Add `ORCIDSettings`.
5. Add `RORSettings`.
6. Add `DOAJSettings`.
7. Add `RetractionWatchSettings`.
8. Add `SnapshotSettings`.
9. Add `AuditSettings`.
10. Add `ThresholdSettings`.
11. Add `LangfuseSettings` or `ObservabilitySettings`.
12. Ensure `get_settings()` remains cached.

**Dependency:** `.env.example` should define the variables first.

---

### `docker/docker-compose.yml`

**Purpose:** Local MVP infra for backend testing.

**Code tasks:**

1. Keep PostgreSQL service from Phase 1.
2. Add Redis service.
3. Add Celery worker service.
4. Add Celery beat service if monthly snapshot update is included.
5. Wire env vars from `.env`.
6. Ensure local volumes do not commit sensitive data.

**MVP minimum:** PostgreSQL + Redis + worker.

---

## 4.2. Schemas and data contracts

### `src/reviewagent/schemas/cms.py`

**Purpose:** Upgrade Canonical Metadata Schema from v1 to v2.0.

**Code tasks:**

1. Preserve Phase 1 fields:
   - DOI
   - title
   - pub year/date
   - journal
   - authors
   - provenance
2. Add article metadata:
   - `abstract`
   - `article_type`
   - `language`
   - `volume`
   - `issue`
   - `pages`
3. Extend `CMSJournal`:
   - `is_scie`
   - `is_ssci`
   - `is_ahci`
   - `is_esci`
   - `is_doaj`
   - `is_predatory`
   - `is_hijacked`
   - `quartile`
   - `sjr_value`
4. Extend `CMSAuthor`:
   - `orcid`
   - `affiliation_raw`
   - `ror_id`
5. Add retraction fields:
   - `is_retracted`
   - `retraction_doi`
   - `retraction_date`
   - `retraction_reason`
6. Add `cms_version = "2.0"`.
7. Keep DOI normalization and provenance validation.
8. Add validators for score-like or date-like fields where needed.

**Important:** Do not make LLM-only fields required. If source APIs do not provide them, they should be nullable or default safe values.

---

### `src/reviewagent/schemas/submission.py`

**Purpose:** Support Phase 2 submission input.

**Code tasks:**

1. Keep Phase 1 DOI request behavior.
2. Add optional/required fields depending product decision:
   - `user_claimed_author`
   - `user_claimed_affiliation`
3. Add/confirm statuses:
   - `PENDING`
   - `PROCESSING`
   - `COMPLETED`
   - `FAILED`
   - `REVIEW_REQUIRED`
4. Extend response with:
   - `submission_id`
   - `status`
   - `decision_id`
   - `review_id` if queued
   - optional `evidence_panel` summary

**MVP recommendation:** Require `doi` and `user_claimed_author`; keep affiliation optional but useful.

---

### `src/reviewagent/schemas/decision.py`

**Purpose:** Extend decision output for multi-agent evidence.

**Code tasks:**

1. Keep labels:
   - `APPROVE`
   - `REVIEW`
   - `REJECT`
2. Add Phase 2 score fields:
   - `metadata_score`
   - `journal_score`
   - `author_score`
   - `retraction_score`
   - `policy_score`
3. Add `confidence_raw` formula support.
4. Add `confidence_calibrated`.
5. Add `evidence_panel` list.
6. Add `verification_checks` for CoVe.
7. Add `self_consistency_samples` if storing sample summaries.
8. Keep `flags` machine-readable.
9. Keep `rationale` grounded and short.

---

### `src/reviewagent/schemas/journal.py`

**Purpose:** Contract for journal quality result.

**Code tasks:**

1. Define `JournalCheckResult`.
2. Fields:
   - `issn_l`
   - `title`
   - `is_indexed`
   - `indexes`
   - `quartile_best`
   - `sjr_value`
   - `is_predatory`
   - `is_hijacked`
   - `flags`
   - `score`
   - `evidence`
3. Validate `score` in `[0, 1]`.
4. Deduplicate `indexes` and `flags`.

---

### `src/reviewagent/schemas/author.py`

**Purpose:** Contract for author/affiliation verification result.

**Code tasks:**

1. Define `AuthorCheckResult`.
2. Fields:
   - `user_claimed_name`
   - `user_claimed_affiliation`
   - `matched_author`
   - `match_method`
   - `match_score`
   - `orcid_verified`
   - `affiliation_match`
   - `flags`
   - `evidence`
3. Define match methods:
   - `orcid`
   - `and_exact`
   - `and_fuzzy`
   - `and_permutation`
   - `none`
4. Validate `match_score` in `[0, 1]`.

---

### `src/reviewagent/schemas/audit.py`

**Purpose:** Contract for WORM audit entries.

**Code tasks:**

1. Define `AuditEntry`.
2. Fields:
   - `entry_id`
   - `sequence`
   - `timestamp`
   - `event_type`
   - `actor`
   - `submission_id`
   - `details`
   - `hmac_hash`
   - `prev_hash`
3. Define event type constants:
   - `submission.created`
   - `decision.created`
   - `review.assigned`
   - `review.overridden`
   - `pipeline.failed`
4. Ensure JSON serialization is deterministic for HMAC.

---

## 4.3. Connectors

### `src/reviewagent/connectors/base.py`

**Purpose:** Shared HTTP behavior for all external APIs.

**Code tasks:**

1. Keep existing async `httpx` behavior.
2. Add configurable connect/read timeout from settings.
3. Add retry helper for safe GET requests.
4. Preserve 404-as-miss behavior where appropriate.
5. Do not hide errors that affect decision evidence.

---

### `src/reviewagent/connectors/crossref.py`

**Purpose:** Primary metadata source, upgraded for CMS v2.

**Code tasks:**

1. Keep DOI lookup.
2. Parse extra fields when available:
   - abstract
   - article type
   - volume/issue/pages
   - ISSN-L/ISSNs
   - ORCID in author records
   - raw affiliation in author records
3. Preserve Phase 1 fallback contract: return `None` if not usable.
4. Populate provenance.

---

### `src/reviewagent/connectors/openalex.py`

**Purpose:** Fallback metadata source, upgraded for CMS v2.

**Code tasks:**

1. Keep DOI lookup fallback.
2. Parse extra fields when available:
   - abstract/inverted abstract if supported
   - publication type
   - host venue/source
   - ISSN-L
   - authorships
   - affiliations/institutions
   - ORCID if exposed
3. Preserve provenance.

---

### `src/reviewagent/connectors/orcid.py`

**Purpose:** Verify whether the claimed author has the DOI in ORCID works.

**Code tasks:**

1. Implement ORCID OAuth client credentials if credentials exist.
2. Support public/sandbox mode if credentials are absent and API allows.
3. Implement `search_author(name)`.
4. Implement `get_works(orcid_id)`.
5. Implement `author_has_work(orcid_id, doi)`.
6. Normalize DOI before matching.
7. Return structured evidence, not just boolean.

**Used by:** `agents/author_agent.py`.

---

### `src/reviewagent/connectors/ror.py`

**Purpose:** Normalize affiliation names and identify institutions.

**Code tasks:**

1. Implement `lookup_affiliation(name)`.
2. Parse ROR ID.
3. Parse normalized organization name.
4. Parse confidence/score if API provides it.
5. Return no-match safely instead of guessing.

**Used by:** `agents/author_agent.py`.

---

### `src/reviewagent/connectors/doaj.py`

**Purpose:** Check whether journal is listed in DOAJ.

**Code tasks:**

1. Implement `check_journal(issn_l)`.
2. Query DOAJ by ISSN.
3. Return:
   - `in_doaj`
   - optional APC info
   - optional seal info
   - source URL/evidence
4. Treat no result as `in_doaj=False`, not connector failure.

**Used by:** `agents/journal_agent.py`.

---

### `src/reviewagent/connectors/retraction_watch.py`

**Purpose:** Check retraction status.

**Code tasks:**

1. Implement `check_retraction(doi)`.
2. Support API or local CSV snapshot depending data availability.
3. Return:
   - `is_retracted`
   - `retraction_doi`
   - `retraction_date`
   - `reason`
   - evidence source
4. Normalize DOI before lookup.

**Used by:** `metadata_agent.py`, `aggregator_agent.py`, or a small dedicated retraction helper.

---

## 4.4. Snapshots

### `src/reviewagent/snapshots/mjl.py`

**Purpose:** Offline Master Journal List lookup.

**Code tasks:**

1. Define `MJLEntry` dataclass.
2. Implement CSV load.
3. Normalize ISSN-L.
4. Store data in dict by ISSN-L.
5. Implement `lookup(issn_l)`.
6. Return SCIE/SSCI/AHCI/ESCI flags.
7. Add safe behavior for missing file in dev/test.

---

### `src/reviewagent/snapshots/scimago.py`

**Purpose:** Offline SCImago SJR/quartile lookup.

**Code tasks:**

1. Define `SCImagoEntry` dataclass.
2. Implement CSV load.
3. Normalize ISSN-L and year.
4. Implement `lookup(issn_l, year)`.
5. If exact year missing, optionally choose nearest previous year only if documented.
6. Return quartile and SJR value.

---

### `src/reviewagent/snapshots/beall.py`

**Purpose:** Offline predatory journal/publisher check.

**Code tasks:**

1. Load Beall-like CSV/list.
2. Normalize journal title.
3. Normalize ISSN.
4. Implement `is_predatory(issn_l, title)`.
5. Return evidence explaining which rule/list matched.

---

### `src/reviewagent/snapshots/updater.py`

**Purpose:** Scheduled snapshot refresh logic.

**Code tasks:**

1. Define update functions per snapshot type.
2. Download to temp path first.
3. Validate basic CSV structure.
4. Atomically replace old snapshot.
5. Emit audit/metric event for update success/failure.
6. Expose callable Celery task through `tasks/snapshot_task.py`.

**MVP note:** If official data access is manual, keep updater able to load local files and document manual refresh.

---

## 4.5. Cache

### `src/reviewagent/cache/redis_client.py`

**Purpose:** Cache DOI metadata and optionally snapshot lookup results.

**Code tasks:**

1. Create Redis async client wrapper.
2. Implement `get_cms(doi)`.
3. Implement `set_cms(doi, cms, ttl=86400)`.
4. Implement `invalidate(doi)`.
5. Use hashed DOI key:
   - `cms:{doi_hash}`
6. Serialize/deserialize Pydantic CMS safely.
7. Fail open if Redis is unavailable: pipeline should continue without cache.

**Used by:** `metadata_agent.py` or `api/routers/submissions.py`.

---

## 4.6. Audit

### `src/reviewagent/audit/worm_logger.py`

**Purpose:** Append-only audit log with HMAC chain.

**Code tasks:**

1. Load `AUDIT__SECRET_KEY` from settings.
2. Implement deterministic payload serialization.
3. Implement `write(event_type, actor, submission_id, details)`.
4. Get previous hash from DB.
5. Compute `hmac_hash = HMAC(secret, payload + prev_hash)`.
6. Persist audit row.
7. Implement `verify_chain()`.
8. Add explicit events:
   - submission created
   - decision created
   - review assigned
   - review overridden
   - pipeline failed

**Used by:** API routers, decision pipeline, reviewer endpoints.

---

## 4.7. Author name disambiguation

### `src/reviewagent/author_nd/vietnamese.py`

**Purpose:** Normalize Vietnamese names for deterministic matching.

**Code tasks:**

1. Unicode NFC normalization.
2. Trim whitespace.
3. Lowercase.
4. Remove academic titles:
   - `GS.`
   - `PGS.`
   - `TS.`
   - `ThS.`
   - English equivalents if needed.
5. Normalize punctuation.
6. Optional diacritic-insensitive version.
7. Return both display-safe and matching-safe strings if useful.

---

### `src/reviewagent/author_nd/disambiguation.py`

**Purpose:** Match claimed author against CMS authors.

**Code tasks:**

1. Implement exact normalized match.
2. Implement fuzzy ratio match.
3. Implement Vietnamese name permutation matching:
   - `Nguyen Van A`
   - `Nguyen V. A.`
   - `A. V. Nguyen`
4. Score all candidate authors.
5. Return best match with score and evidence.
6. Add flags for:
   - `NO_AUTHOR_MATCH`
   - `LOW_AUTHOR_MATCH_SCORE`
   - `MULTIPLE_AUTHOR_CANDIDATES`

---

### `src/reviewagent/author_nd/embeddings.py`

**Purpose:** Optional semantic fallback for difficult author matching.

**Code tasks:**

1. Keep this optional for MVP.
2. Define interface like `score_name_similarity(a, b)`.
3. If no local model is configured, return `None` or skip.
4. Do not make heavy model loading required for normal pipeline startup.

**MVP recommendation:** Implement deterministic matching first; leave embeddings as optional fallback.

---

## 4.8. Agents

### `src/reviewagent/agents/state.py`

**Purpose:** Shared state for LangGraph pipeline.

**Code tasks:**

1. Extend Phase 1 `ReviewState`.
2. Add:
   - `user_claimed_author`
   - `user_claimed_affiliation`
   - `journal_result`
   - `author_result`
   - `aggregated_scores`
   - `evidence_panel`
   - `timing`
   - `audit_events`
3. Keep:
   - `submission_id`
   - `doi`
   - `cms`
   - `decision`
   - `errors`
   - `metadata_source`
   - `prompt_version`
4. Decide whether to use `TypedDict` or dataclass consistently with LangGraph.

---

### `src/reviewagent/agents/metadata_agent.py`

**Purpose:** Fetch and normalize publication metadata.

**Code tasks:**

1. Check Redis cache first if injected/configured.
2. If cache miss, call Crossref.
3. If Crossref fails/misses, call OpenAlex.
4. Map result to CMS v2.0.
5. Enrich author ORCID/affiliation fields when source provides them.
6. Call Retraction Watch or leave retraction enrichment to aggregator.
7. Write CMS to cache.
8. Return structured result with errors and source.

**Phase 1 continuity:** Crossref -> OpenAlex fallback remains unchanged conceptually.

---

### `src/reviewagent/agents/router_agent.py`

**Purpose:** Decide which agents should run.

**Code tasks:**

1. Always require metadata path.
2. Run journal check only when CMS has journal title or ISSN-L.
3. Run author check only when user supplied claimed author.
4. Add safe skip reasons into state.
5. Use LangGraph `Send` or equivalent routing pattern.

**Important design point:** In many cases journal/author agents need CMS first. The router can fan out only after metadata is available, or graph can use a two-stage flow:

```text
metadata first
  -> route journal + author in parallel
  -> aggregator
  -> decision
```

This is usually safer than launching journal/author before CMS exists.

---

### `src/reviewagent/agents/journal_agent.py`

**Purpose:** Layer 2 journal quality verification.

**Code tasks:**

1. Read CMS journal fields.
2. Extract ISSN-L and publication year.
3. Lookup MJL.
4. Lookup SCImago.
5. Query DOAJ.
6. Check Beall/predatory list.
7. Check hijacked list if available.
8. Compute journal score:
   - predatory/hijacked -> 0
   - indexed SCIE/SSCI/AHCI -> strong positive
   - ESCI/DOAJ -> medium positive
   - Q1/Q2/Q3 boosts
9. Build `JournalCheckResult`.
10. Add flags:
   - `NOT_INDEXED`
   - `PREDATORY`
   - `HIJACKED`
   - `LOW_QUARTILE`
   - `MISSING_ISSN`

---

### `src/reviewagent/agents/author_agent.py`

**Purpose:** Layer 3 author and affiliation verification.

**Code tasks:**

1. Read claimed author and affiliation from state.
2. Read CMS authors.
3. If CMS author has ORCID, verify DOI in ORCID works.
4. If no ORCID match, run deterministic AND pipeline:
   - normalize claimed name
   - normalize CMS author names
   - exact match
   - fuzzy match
   - permutation match
5. Normalize affiliation through ROR if claimed affiliation exists.
6. Compare claimed affiliation with CMS affiliation evidence if available.
7. Compute author score.
8. Build `AuthorCheckResult`.
9. Add flags:
   - `NO_AUTHOR_MATCH`
   - `AFFILIATION_MISMATCH`
   - `NO_AFFILIATION_EVIDENCE`
   - `ORCID_LOOKUP_FAILED`

---

### `src/reviewagent/agents/aggregator_agent.py`

**Purpose:** Merge all agent outputs before final decision.

**Code tasks:**

1. Read CMS.
2. Read `JournalCheckResult`.
3. Read `AuthorCheckResult`.
4. Read retraction info.
5. Compute:
   - `metadata_score`
   - `journal_score`
   - `author_score`
   - `retraction_score`
   - `policy_score`
6. Build `evidence_panel` as list of evidence items.
7. Merge flags from all agents.
8. Store `aggregated_scores` in state.
9. Ensure missing evidence lowers confidence or routes to `REVIEW`.

---

### `src/reviewagent/agents/decision_agent.py`

**Purpose:** Final grounded decision v2.

**Code tasks:**

1. Keep Phase 1 rule-based fallback.
2. Add deterministic Phase 2 formula:

```text
confidence_raw =
  0.25 * metadata_score
+ 0.25 * journal_score
+ 0.30 * author_score
+ 0.10 * retraction_score
+ 0.10 * policy_score
```

3. Use Platt scaling:

```text
confidence_calibrated = sigmoid(A * confidence_raw + B)
```

4. Apply thresholds:
   - `>= THRESHOLD__AUTO_APPROVE` -> `APPROVE`
   - between reject and approve threshold -> `REVIEW`
   - `< THRESHOLD__AUTO_REJECT` -> `REJECT`
5. Add hard override rules:
   - retracted -> `REJECT`
   - predatory/hijacked -> `REJECT` or strong `REVIEW` depending policy
   - no author match -> `REVIEW`
6. Add CoVe if enabled:
   - generate rationale
   - verify each claim against evidence fields
   - reduce confidence if claim unsupported
7. Add self-consistency if enabled:
   - run k samples
   - majority vote label
   - average calibrated confidence
8. Return `DecisionResult`.

---

### `src/reviewagent/agents/graph.py`

**Purpose:** MVP orchestration with LangGraph.

**Recommended safe graph shape:**

```text
START
  -> metadata_agent
  -> router_agent
  -> journal_agent and/or author_agent in parallel
  -> aggregator_agent
  -> decision_agent
  -> END
```

**Code tasks:**

1. Build a `StateGraph` using extended `ReviewState`.
2. Add nodes:
   - metadata
   - router
   - journal
   - author
   - aggregator
   - decision
3. Use conditional routing after metadata.
4. Ensure aggregator acts as barrier.
5. Add timeout/retry where safe.
6. Preserve a simple `ReviewPipeline.run()` interface for API.
7. Return final state to API.

**Why metadata first:** Journal and author checks usually need CMS fields. This avoids running agents without data.

---

## 4.9. LLM layer

### `src/reviewagent/llm/prompts/decision_v2.py`

**Purpose:** Prompt for grounded Phase 2 decision with verification checks.

**Code tasks:**

1. Define system prompt:
   - use only provided evidence
   - do not invent metadata
   - fail safe to `REVIEW`
   - produce JSON only
2. Define user prompt builder from:
   - CMS summary
   - aggregated scores
   - journal result
   - author result
   - retraction info
   - flags
3. Require output fields:
   - decision
   - confidence
   - rationale
   - verification_checks
   - cited evidence IDs/fields
4. Keep rationale concise.

---

### `src/reviewagent/llm/prompts/metadata_v1.py`

**Purpose:** Optional prompt for metadata normalization when source fields are messy.

**Code tasks:**

1. Use only raw source payload fields.
2. Do not allow model to fill missing facts from memory.
3. Output normalized field candidates only.
4. Mark uncertainty explicitly.

**MVP caution:** Prefer deterministic mapping in connectors. Use this prompt only if really needed.

---

### `src/reviewagent/llm/calibration.py`

**Purpose:** Real confidence calibration.

**Code tasks:**

1. Replace identity function with Platt scaling.
2. Keep constants configurable or documented:
   - `A`
   - `B`
3. Clamp output to `[0, 1]`.
4. Add tests for edge values.
5. Later, fit A/B from gold dataset.

---

### `src/reviewagent/llm/gateway.py`

**Purpose:** LLM call wrapper for v2 prompts and tracing.

**Code tasks:**

1. Keep Phase 1 structured JSON parsing.
2. Add `generate_decision_v2()`.
3. Add optional Langfuse trace wrapper.
4. Add self-consistency call helper.
5. Add strict schema parsing to `DecisionResult`.
6. Preserve fallback when LLM is not configured.

---

## 4.10. Database layer

### `src/reviewagent/db/session.py`

**Purpose:** DB engine/session base.

**Code tasks:**

1. Keep async SQLAlchemy setup.
2. Prepare for Alembic migrations.
3. Ensure all new models are imported through `db/models/__init__.py`.

---

### `src/reviewagent/db/models/submission.py`

**Purpose:** Store submission request and lifecycle.

**Code tasks:**

1. Keep DOI/status fields.
2. Add:
   - `user_claimed_author`
   - `user_claimed_affiliation`
   - `review_status` if needed
   - `assigned_reviewer_id` if doing reviewer assignment
3. Keep timestamps.

---

### `src/reviewagent/db/models/publication.py`

**Purpose:** Store CMS v2 cache by DOI.

**Code tasks:**

1. Keep unique DOI.
2. Store CMS v2 JSON.
3. Store source/provenance JSON.
4. Add fields useful for query:
   - `title`
   - `pub_year`
   - `journal_title`
   - `issn_l`
   - `is_retracted`

---

### `src/reviewagent/db/models/decision.py`

**Purpose:** Store final decision.

**Code tasks:**

1. Keep Phase 1 decision fields.
2. Add Phase 2 fields:
   - `metadata_score`
   - `journal_score`
   - `author_score`
   - `retraction_score`
   - `policy_score`
   - `evidence_panel`
   - `verification_checks`
   - `decision_source` such as `rule_based`, `llm_cove`, `llm_self_consistency`
3. Keep prompt/model version.

---

### `src/reviewagent/db/models/journal.py`

**Purpose:** Store journal check results.

**Code tasks:**

1. Define `journal_checks` table.
2. Fields:
   - `id`
   - `publication_id`
   - `issn_l`
   - `indexes`
   - `quartile_best`
   - `sjr_value`
   - `is_predatory`
   - `is_hijacked`
   - `score`
   - `evidence`
   - timestamps
3. Add relationship to publication.

---

### `src/reviewagent/db/models/audit_log.py`

**Purpose:** Store WORM audit entries.

**Code tasks:**

1. Define `audit_log` table.
2. Fields:
   - `id`
   - `sequence`
   - `timestamp`
   - `event_type`
   - `actor`
   - `submission_id`
   - `details`
   - `hmac_hash`
   - `prev_hash`
3. Add index on:
   - `submission_id`
   - `event_type`
   - `sequence`

---

### `src/reviewagent/db/models/user.py`

**Purpose:** Minimal reviewer identity if reviewer endpoints need assignment.

**Code tasks:**

1. Keep minimal for MVP.
2. Fields:
   - `id`
   - `email`
   - `display_name`
   - `role`
   - `is_active`
3. Do not build full auth system unless required.

---

### `src/reviewagent/db/repositories/submission_repo.py`

**Purpose:** CRUD for submissions.

**Code tasks:**

1. Keep create/get/update status.
2. Add query for review queue:
   - submissions with latest decision `REVIEW`
3. Add update assignment if reviewer assignment exists.
4. Add pagination helpers.

---

### `src/reviewagent/db/repositories/decision_repo.py`

**Purpose:** CRUD for decisions.

**Code tasks:**

1. Keep save/get by ID/submission.
2. Add save v2 evidence.
3. Add update/override decision for reviewer.
4. Preserve original automated decision in audit trail.

---

### `src/reviewagent/db/repositories/publication_repo.py`

**Purpose:** CRUD for publication/CMS cache.

**Code tasks:**

1. Add if not already complete.
2. Get by DOI.
3. Upsert CMS v2 by DOI.
4. Link publication to submission.

---

### `src/reviewagent/db/repositories/journal_repo.py`

**Purpose:** CRUD for journal checks.

**Code tasks:**

1. Create journal check.
2. Get latest by publication ID.
3. Get by ISSN-L.
4. Optional cache reuse by ISSN-L and year.

---

### Alembic migration files

**Purpose:** Replace Phase 1 `create_all` style with schema migrations.

**Code tasks:**

1. Initialize Alembic if not present.
2. Create migration for Phase 1 existing tables if needed.
3. Create Phase 2 migration:
   - alter submissions
   - alter publications
   - alter decisions
   - create journal_checks
   - create audit_log
   - create users if needed
4. Test upgrade and downgrade locally.

---

## 4.11. API layer

### `src/reviewagent/api/deps.py`

**Purpose:** FastAPI dependencies.

**Code tasks:**

1. Keep DB session dependency.
2. Keep settings dependency.
3. Add Redis dependency if used directly in routers.
4. Add pipeline dependency for Phase 2 graph.
5. Add WORM logger dependency.
6. Add current user/reviewer dependency if reviewer endpoints need auth.

---

### `src/reviewagent/api/main.py`

**Purpose:** FastAPI app factory.

**Code tasks:**

1. Include existing health/submissions/decisions routers.
2. Include `reviews` router.
3. Add middleware if implemented.
4. Add `/metrics` endpoint or Prometheus ASGI integration.
5. Load snapshots during lifespan if required.
6. Cleanly close Redis/HTTP clients if app owns them.

---

### `src/reviewagent/api/routers/submissions.py`

**Purpose:** Submission creation endpoint.

**Code tasks:**

1. Accept DOI + claimed author + claimed affiliation.
2. Create submission record.
3. Write `submission.created` audit event.
4. Choose sync or async mode:
   - sync: run pipeline immediately and return completed decision
   - async: enqueue Celery and return `PROCESSING`
5. Save publication, journal check, decision.
6. If decision is `REVIEW`, mark for reviewer queue.
7. Return evidence summary.

**MVP recommendation:** Support sync first, then add Celery path. This keeps debugging simpler.

---

### `src/reviewagent/api/routers/decisions.py`

**Purpose:** Read decisions.

**Code tasks:**

1. Keep get by decision ID.
2. Keep get by submission ID.
3. Return Phase 2 fields:
   - sub-scores
   - evidence panel
   - flags
   - verification checks
   - review status
4. Do not expose secret audit HMAC key.

---

### `src/reviewagent/api/routers/reviews.py`

**Purpose:** Backend reviewer queue API, no frontend.

**Code tasks:**

1. `GET /reviews`
   - list pending review items
   - filter by status
   - pagination
2. `GET /reviews/{review_id}`
   - show submission, CMS summary, decision, evidence panel
3. `POST /reviews/{review_id}/assign`
   - assign reviewer
   - write audit event
4. `POST /reviews/{review_id}/decide`
   - reviewer chooses `APPROVE` or `REJECT`
   - require reviewer note
   - update final decision/override field
   - write `review.overridden` audit event
5. `GET /reviews/stats`
   - pending count
   - completed count
   - average response time if easy

---

### `src/reviewagent/api/routers/health.py`

**Purpose:** Health endpoint.

**Code tasks:**

1. Keep app + DB health.
2. Add optional Redis status.
3. Add snapshot loaded status.
4. Keep response lightweight.

---

### `src/reviewagent/api/middleware.py`

**Purpose:** Backend middleware.

**Code tasks:**

1. Add request logging middleware.
2. Add CORS if needed for future dashboard, but keep config controlled.
3. Add auth middleware only if a clear auth strategy is selected.
4. Avoid building full SSO in MVP unless explicitly required.

---

## 4.12. Tasks and async workers

### `src/reviewagent/tasks/celery_app.py`

**Purpose:** Celery app factory.

**Code tasks:**

1. Load broker/backend from settings.
2. Configure task routes.
3. Configure serialization as JSON.
4. Register review and snapshot tasks.

---

### `src/reviewagent/tasks/review_task.py`

**Purpose:** Run review pipeline in background.

**Code tasks:**

1. Define `run_review_pipeline(submission_id, doi)`.
2. Open DB session inside task.
3. Load submission fields.
4. Run `ReviewPipeline`.
5. Save CMS/decision/journal check.
6. Update submission status.
7. Write audit events.
8. Retry safe transient failures.
9. Mark `FAILED` on final failure.

---

### `src/reviewagent/tasks/snapshot_task.py`

**Purpose:** Scheduled snapshot updates.

**Code tasks:**

1. Define `update_all_snapshots()`.
2. Call `snapshots/updater.py` functions.
3. Emit logs/metrics.
4. Avoid corrupting existing snapshots on failed download.

---

## 4.13. Observability

### `src/reviewagent/observability/metrics.py`

**Purpose:** Prometheus metrics.

**Code tasks:**

1. Define counters:
   - submissions total
   - decisions by label
   - connector errors by source
2. Define histograms:
   - pipeline duration
   - connector latency
   - LLM latency
3. Define gauges:
   - pending reviews
   - worker health if easy
4. Expose metrics through API.

---

### `src/reviewagent/observability/tracing.py`

**Purpose:** Langfuse tracing for LLM calls.

**Code tasks:**

1. Initialize Langfuse client only when configured.
2. Provide context manager/helper:
   - `trace_llm_call(agent_name, prompt_version, input_data)`
3. Capture:
   - model
   - prompt version
   - latency
   - token usage if available
   - output status
4. Do not log secrets.
5. Do not log unnecessary personal data beyond required audit context.

---

## 4.14. Scripts

### `scripts/seed_snapshots.py`

**Purpose:** Load/download snapshot data for local/dev MVP.

**Code tasks:**

1. CLI args:
   - `--all`
   - `--mjl`
   - `--scimago`
   - `--beall`
   - `--doaj`
2. Validate file paths.
3. Load CSV and print counts.
4. Optionally write normalized local cache.
5. Exit non-zero when required snapshot is invalid.

---

### `scripts/eval.py`

**Purpose:** Upgrade evaluation for Phase 2.

**Code tasks:**

1. Keep Phase 1 eval behavior.
2. Add `--phase2` flag.
3. Load gold dataset with:
   - DOI
   - claimed author
   - claimed affiliation
   - expected decision
   - expected flags if available
4. Run pipeline.
5. Compute:
   - precision
   - recall
   - F1
   - decision distribution
   - average latency
   - cost estimate if LLM usage available
6. Output JSON report.

---

### `scripts/migrate.py`

**Purpose:** Existing Phase 1 migration helper.

**Phase 2 decision:** Prefer Alembic. Keep this script only as a dev helper or deprecate it clearly after Alembic is working.

---

## 4.15. Tests

### `tests/unit/test_schemas.py`

**Purpose:** Existing schema tests plus Phase 2 schema coverage.

**Add tests for:**

1. CMS v2 accepts journal/author/retraction fields.
2. Journal result score validation.
3. Author result match method validation.
4. Audit entry serialization shape.
5. Submission request accepts claimed author/affiliation.

---

### `tests/unit/test_journal_agent.py`

**Purpose:** Unit-test journal scoring.

**Test cases:**

1. SCIE Q1 journal gets high score.
2. DOAJ-only journal gets medium score.
3. Predatory journal gets zero score and flag.
4. Hijacked journal gets zero score and flag.
5. Missing ISSN routes to review-style low score/flag.

---

### `tests/unit/test_author_agent.py`

**Purpose:** Unit-test author verification.

**Test cases:**

1. Exact Vietnamese normalized name match.
2. Fuzzy name match.
3. Name permutation match.
4. ORCID DOI match.
5. Affiliation mismatch flag.
6. No author match flag.

---

### `tests/unit/test_worm_logger.py`

**Purpose:** Unit-test audit integrity.

**Test cases:**

1. Writes first audit entry with genesis previous hash.
2. Writes second entry linked to first.
3. `verify_chain()` returns true for untouched entries.
4. Tampered entry fails verification.

---

### `tests/unit/test_cache.py`

**Purpose:** Unit-test Redis cache wrapper with fake Redis or mocked client.

**Test cases:**

1. Set/get CMS roundtrip.
2. Missing key returns `None`.
3. Redis failure does not crash pipeline if fail-open is intended.

---

### `tests/unit/test_connectors_phase2.py`

**Purpose:** Unit-test new connector parsing with mocked HTTP.

**Test cases:**

1. ORCID search parse.
2. ORCID works DOI match.
3. ROR affiliation parse.
4. DOAJ ISSN match.
5. Retraction Watch positive and negative result.

---

### `tests/integration/test_langgraph_pipeline.py`

**Purpose:** Test full Phase 2 graph with mocked connectors/snapshots.

**Test cases:**

1. Happy path returns `APPROVE` with metadata, journal, author evidence.
2. Missing author match returns `REVIEW`.
3. Predatory journal returns `REJECT` or configured policy result.
4. Retraction returns `REJECT`.

---

### `tests/integration/test_submissions_api_phase2.py`

**Purpose:** Test API submission flow.

**Test cases:**

1. POST submission accepts DOI + author + affiliation.
2. Response includes decision/evidence in sync mode.
3. REVIEW decision appears in review queue.
4. Failure updates submission status.

---

### `tests/integration/test_reviewer_api.py`

**Purpose:** Test reviewer endpoints.

**Test cases:**

1. List pending reviews.
2. Get review detail.
3. Assign reviewer.
4. Reviewer override writes audit event.
5. Final decision reflects reviewer action.

---

### `tests/gold_dataset/seed_100.json`

**Purpose:** Gold dataset for F1 target.

**Data shape per item:**

```json
{
  "doi": "10.xxxx/yyyy",
  "user_claimed_author": "Nguyen Van A",
  "user_claimed_affiliation": "PTIT",
  "expected_decision": "APPROVE",
  "expected_flags": [],
  "notes": "Human annotated evidence summary"
}
```

---

## 5. Recommended coding order

This order minimizes broken imports and makes each stage testable.

### Stage 1 — Foundation

1. `pyproject.toml`
2. `.env.example`
3. `src/reviewagent/config.py`
4. `docker/docker-compose.yml`

**Verify:** Import settings and start PostgreSQL/Redis locally.

---

### Stage 2 — Core schemas

5. `src/reviewagent/schemas/journal.py`
6. `src/reviewagent/schemas/author.py`
7. `src/reviewagent/schemas/audit.py`
8. `src/reviewagent/schemas/cms.py`
9. `src/reviewagent/schemas/submission.py`
10. `src/reviewagent/schemas/decision.py`

**Verify:** Run schema unit tests.

---

### Stage 3 — Connectors and deterministic source parsing

11. `src/reviewagent/connectors/base.py`
12. `src/reviewagent/connectors/crossref.py`
13. `src/reviewagent/connectors/openalex.py`
14. `src/reviewagent/connectors/orcid.py`
15. `src/reviewagent/connectors/ror.py`
16. `src/reviewagent/connectors/doaj.py`
17. `src/reviewagent/connectors/retraction_watch.py`

**Verify:** Mocked connector tests. Do not depend on live APIs for normal CI.

---

### Stage 4 — Snapshots and cache

18. `src/reviewagent/snapshots/mjl.py`
19. `src/reviewagent/snapshots/scimago.py`
20. `src/reviewagent/snapshots/beall.py`
21. `src/reviewagent/snapshots/updater.py`
22. `src/reviewagent/cache/redis_client.py`
23. `scripts/seed_snapshots.py`

**Verify:** Load small fixture CSVs and test lookup behavior.

---

### Stage 5 — Audit and author matching utilities

24. `src/reviewagent/audit/worm_logger.py`
25. `src/reviewagent/author_nd/vietnamese.py`
26. `src/reviewagent/author_nd/disambiguation.py`
27. `src/reviewagent/author_nd/embeddings.py` optional

**Verify:** WORM chain tests and author matching unit tests.

---

### Stage 6 — Database models and migrations

28. `src/reviewagent/db/models/submission.py`
29. `src/reviewagent/db/models/publication.py`
30. `src/reviewagent/db/models/decision.py`
31. `src/reviewagent/db/models/journal.py`
32. `src/reviewagent/db/models/audit_log.py`
33. `src/reviewagent/db/models/user.py` if reviewer assignment needs users
34. `src/reviewagent/db/models/__init__.py`
35. Alembic migration files

**Verify:** Alembic upgrade on clean DB.

---

### Stage 7 — Repositories

36. `src/reviewagent/db/repositories/publication_repo.py`
37. `src/reviewagent/db/repositories/submission_repo.py`
38. `src/reviewagent/db/repositories/decision_repo.py`
39. `src/reviewagent/db/repositories/journal_repo.py`

**Verify:** Repository tests with test DB.

---

### Stage 8 — Agents

40. `src/reviewagent/agents/state.py`
41. `src/reviewagent/agents/metadata_agent.py`
42. `src/reviewagent/agents/journal_agent.py`
43. `src/reviewagent/agents/author_agent.py`
44. `src/reviewagent/agents/aggregator_agent.py`
45. `src/reviewagent/agents/decision_agent.py`
46. `src/reviewagent/agents/router_agent.py`
47. `src/reviewagent/agents/graph.py`

**Verify:** Agent unit tests first, then mocked full graph integration tests.

---

### Stage 9 — LLM v2

48. `src/reviewagent/llm/prompts/decision_v2.py`
49. `src/reviewagent/llm/prompts/metadata_v1.py` optional
50. `src/reviewagent/llm/calibration.py`
51. `src/reviewagent/llm/gateway.py`

**Verify:** Structured output parsing tests and fallback behavior without LLM key.

---

### Stage 10 — API

52. `src/reviewagent/api/deps.py`
53. `src/reviewagent/api/routers/health.py`
54. `src/reviewagent/api/routers/submissions.py`
55. `src/reviewagent/api/routers/decisions.py`
56. `src/reviewagent/api/routers/reviews.py`
57. `src/reviewagent/api/middleware.py`
58. `src/reviewagent/api/main.py`

**Verify:** FastAPI integration tests.

---

### Stage 11 — Celery tasks

59. `src/reviewagent/tasks/celery_app.py`
60. `src/reviewagent/tasks/review_task.py`
61. `src/reviewagent/tasks/snapshot_task.py`

**Verify:** Run worker locally and execute one pipeline task.

---

### Stage 12 — Observability

62. `src/reviewagent/observability/metrics.py`
63. `src/reviewagent/observability/tracing.py`

**Verify:** `/metrics` returns Prometheus output; LLM tracing is skipped safely when not configured.

---

### Stage 13 — Evaluation and final tests

64. `scripts/eval.py`
65. `tests/unit/test_schemas.py`
66. `tests/unit/test_journal_agent.py`
67. `tests/unit/test_author_agent.py`
68. `tests/unit/test_worm_logger.py`
69. `tests/unit/test_cache.py`
70. `tests/unit/test_connectors_phase2.py`
71. `tests/integration/test_langgraph_pipeline.py`
72. `tests/integration/test_submissions_api_phase2.py`
73. `tests/integration/test_reviewer_api.py`
74. `tests/gold_dataset/seed_100.json`

**Verify:** Full test suite and Phase 2 eval.

---

## 6. Smaller task breakdown by milestone

## Milestone A — Make Phase 2 contracts compile

Goal: All Phase 2 schemas and settings import without touching runtime behavior.

Tasks:

1. Add Phase 2 settings.
2. Add journal schema.
3. Add author schema.
4. Add audit schema.
5. Upgrade CMS schema.
6. Upgrade submission schema.
7. Upgrade decision schema.
8. Add schema tests.

Success criteria:

- `pytest tests/unit/test_schemas.py -v` passes.
- `python -c "from reviewagent.config import get_settings; print(get_settings().app.name)"` works.

---

## Milestone B — Add source integrations without agents

Goal: Each connector/snapshot can independently return normalized evidence.

Tasks:

1. Upgrade Crossref parser.
2. Upgrade OpenAlex parser.
3. Implement ORCID connector.
4. Implement ROR connector.
5. Implement DOAJ connector.
6. Implement Retraction Watch connector.
7. Implement MJL snapshot.
8. Implement SCImago snapshot.
9. Implement Beall snapshot.
10. Add mocked tests.

Success criteria:

- Connector tests pass without live network.
- Snapshot tests pass with small fixture CSVs.

---

## Milestone C — Add cache, audit, and author matching utilities

Goal: Non-agent support modules are usable.

Tasks:

1. Implement Redis cache wrapper.
2. Implement WORM logger.
3. Implement Vietnamese name normalization.
4. Implement deterministic author disambiguation.
5. Keep embeddings optional.
6. Add unit tests.

Success criteria:

- Cache roundtrip test passes with fake Redis/mocked client.
- WORM tamper test fails as expected.
- Author matching tests cover exact/fuzzy/permutation cases.

---

## Milestone D — Add DB schema and repositories

Goal: Database can store all Phase 2 evidence.

Tasks:

1. Extend submissions table.
2. Extend publications table.
3. Extend decisions table.
4. Add journal checks table.
5. Add audit log table.
6. Add optional users table.
7. Add Alembic migration.
8. Extend repositories.

Success criteria:

- Alembic upgrade succeeds on clean DB.
- Repository tests can create submission -> publication -> decision -> audit log.

---

## Milestone E — Build agents one by one

Goal: Each agent works independently before graph orchestration.

Tasks:

1. Extend `ReviewState`.
2. Upgrade metadata agent.
3. Implement journal agent.
4. Implement author agent.
5. Implement aggregator agent.
6. Upgrade decision agent.
7. Add unit tests for each.

Success criteria:

- Each agent test passes with injected fake dependencies.
- Decision agent returns `REVIEW` for missing evidence.

---

## Milestone F — Build full graph

Goal: Pipeline runs end-to-end with mocked dependencies.

Tasks:

1. Build metadata-first LangGraph.
2. Add router after metadata.
3. Fan out journal and author checks.
4. Join at aggregator.
5. Run decision agent.
6. Return final state.
7. Add integration tests.

Success criteria:

- Happy path returns decision with evidence panel.
- Missing author match routes to `REVIEW`.
- Retracted article routes to `REJECT`.

---

## Milestone G — Wire API

Goal: Backend API exposes Phase 2 pipeline.

Tasks:

1. Update dependencies.
2. Update submission endpoint.
3. Update decision endpoint.
4. Add review queue endpoint.
5. Add review decision endpoint.
6. Add audit writes.
7. Add health checks.
8. Add API tests.

Success criteria:

- `POST /submissions` accepts DOI + author + affiliation.
- `GET /decisions/{id}` returns Phase 2 evidence.
- `GET /reviews` shows REVIEW cases.
- `POST /reviews/{id}/decide` creates audit event.

---

## Milestone H — Add async worker path

Goal: Long-running reviews can run in Celery.

Tasks:

1. Configure Celery app.
2. Implement review task.
3. Implement snapshot task.
4. Add async mode to submission endpoint.
5. Update docker compose.
6. Add worker smoke test.

Success criteria:

- Celery worker can process one submission.
- API returns `PROCESSING` when async mode is used.
- Submission eventually becomes `COMPLETED` or `REVIEW_REQUIRED`.

---

## Milestone I — Add metrics, tracing, and eval

Goal: MVP can be measured.

Tasks:

1. Add Prometheus metrics.
2. Add `/metrics` endpoint.
3. Add Langfuse tracing around LLM calls.
4. Upgrade eval script.
5. Create seed gold dataset.
6. Run eval.

Success criteria:

- `/metrics` returns metrics.
- LLM calls do not crash when Langfuse is not configured.
- Eval reports precision/recall/F1/latency.

---

## 7. Dependency graph summary

```text
config.py
  -> all runtime modules

schemas/cms.py
  -> connectors
  -> agents
  -> cache
  -> db publication model

schemas/journal.py
  -> journal_agent
  -> db journal model/repo

schemas/author.py
  -> author_agent

schemas/audit.py
  -> worm_logger
  -> audit_log model

connectors/base.py
  -> crossref/openalex/orcid/ror/doaj/retraction_watch

snapshots/mjl.py
snapshots/scimago.py
snapshots/beall.py
  -> journal_agent
  -> snapshots/updater.py

cache/redis_client.py
  -> metadata_agent
  -> submissions router optionally

author_nd/vietnamese.py
  -> author_nd/disambiguation.py
  -> author_agent

audit/worm_logger.py
  -> submissions router
  -> reviews router
  -> review_task

agents/state.py
  -> all agents
  -> graph.py

metadata_agent.py
  -> crossref/openalex/retraction/cache/cms

journal_agent.py
  -> journal schema + snapshots + doaj

author_agent.py
  -> author schema + orcid + ror + author_nd

aggregator_agent.py
  -> CMS + journal + author + decision evidence

decision_agent.py
  -> decision schema + llm gateway + calibration

agents/graph.py
  -> all agents
  -> API deps
  -> Celery task

db/models/*
  -> repositories
  -> Alembic

repositories/*
  -> API routers
  -> Celery tasks

api/deps.py
  -> routers

api/main.py
  -> all routers + middleware + metrics
```

---

## 8. Minimal Phase 2 MVP definition

Phase 2 can be considered minimally complete when all of these are true:

1. `POST /submissions` accepts:
   - DOI
   - claimed author
   - claimed affiliation
2. Metadata still comes from Crossref/OpenAlex with provenance.
3. Journal agent checks at least:
   - MJL
   - SCImago
   - DOAJ
   - Beall/predatory flag
4. Author agent checks at least:
   - deterministic name matching
   - ORCID when available
   - affiliation comparison when evidence exists
5. Aggregator produces:
   - sub-scores
   - evidence panel
   - flags
6. Decision agent produces:
   - `APPROVE`, `REVIEW`, or `REJECT`
   - calibrated confidence
   - grounded rationale
7. REVIEW decisions are visible through backend review endpoints.
8. Reviewer override writes audit log.
9. WORM audit chain can be verified.
10. Redis cache is used but failure does not break the pipeline.
11. Tests cover schemas, agents, audit, and API.
12. Eval script can run Phase 2 dataset and report F1.

---

## 9. Suggested implementation guardrails

1. Do not make all Phase 2 modules production-perfect on first pass.
2. Implement deterministic logic before LLM logic.
3. Use dependency injection for connectors so tests can mock sources.
4. Avoid live API calls in unit tests.
5. Keep Redis/Celery optional until the sync pipeline is correct.
6. Do not add frontend-specific response shapes beyond what backend needs.
7. Do not implement appeals/reports unless Phase 3 is explicitly requested.
8. Treat placeholder files as empty until inspected.
9. Keep evidence explicit: every score should be explainable from a source field.
10. When unsure, route to `REVIEW`.

---

## 10. Final checklist

### Foundation

- [ ] `pyproject.toml` has Phase 2 dependencies.
- [ ] `.env.example` has Phase 2 variables.
- [ ] `config.py` has typed Phase 2 settings.
- [ ] Docker Compose includes PostgreSQL + Redis + Celery worker.

### Schemas

- [ ] CMS v2.0 supports journal, author, retraction fields.
- [ ] Submission schema supports claimed author/affiliation.
- [ ] Decision schema supports sub-scores and evidence panel.
- [ ] Journal schema exists.
- [ ] Author schema exists.
- [ ] Audit schema exists.

### Connectors and snapshots

- [ ] Crossref parser upgraded.
- [ ] OpenAlex parser upgraded.
- [ ] ORCID connector implemented.
- [ ] ROR connector implemented.
- [ ] DOAJ connector implemented.
- [ ] Retraction Watch connector implemented.
- [ ] MJL snapshot lookup implemented.
- [ ] SCImago snapshot lookup implemented.
- [ ] Beall/predatory lookup implemented.

### Cache, audit, and author matching

- [ ] Redis CMS cache implemented.
- [ ] WORM logger implemented.
- [ ] Vietnamese name normalization implemented.
- [ ] Author disambiguation implemented.

### Agents

- [ ] ReviewState extended.
- [ ] Metadata agent upgraded.
- [ ] Journal agent implemented.
- [ ] Author agent implemented.
- [ ] Aggregator agent implemented.
- [ ] Decision agent v2 implemented.
- [ ] Router agent implemented.
- [ ] LangGraph pipeline implemented.

### DB/API/tasks

- [ ] Phase 2 DB models/migrations implemented.
- [ ] Repositories updated.
- [ ] Submission API updated.
- [ ] Decision API updated.
- [ ] Review API added.
- [ ] Celery app/task added.
- [ ] Snapshot task added.

### Observability/eval/tests

- [ ] Prometheus metrics added.
- [ ] Langfuse tracing added as optional.
- [ ] Eval script supports Phase 2.
- [ ] Unit tests added.
- [ ] Integration tests added.
- [ ] Gold dataset seed added.

---

## 11. Recommended first implementation slice after this document

When starting actual coding, the safest first slice is:

1. Settings + schemas only.
2. Tests for schemas.
3. No connectors yet.
4. No graph changes yet.

Reason: this creates stable contracts for all later work and avoids breaking the working Phase 1 pipeline too early.
