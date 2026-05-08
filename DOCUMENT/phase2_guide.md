# Phase 2 MVP — Hướng dẫn chi tiết

Tài liệu này dành cho developer muốn hiểu toàn bộ Phase 2 MVP của ReviewAgent PTIT: mở rộng từ PoC lên hệ thống nội bộ có thể dùng thực tế với 5 lớp kiến trúc đầy đủ.

---

## Mục lục

1. [Tổng quan nghiệp vụ](#1-tổng-quan-nghiệp-vụ)
2. [Khác biệt chính so với Phase 1](#2-khác-biệt-chính-so-với-phase-1)
3. [Cách chạy toàn bộ Phase 2](#3-cách-chạy-toàn-bộ-phase-2)
4. [Sơ đồ luồng dữ liệu](#4-sơ-đồ-luồng-dữ-liệu)
5. [Chi tiết từng file — vai trò và chức năng](#5-chi-tiết-từng-file)
6. [Thứ tự code và dependency](#6-thứ-tự-code-và-dependency)
7. [Cách test từng phần](#7-cách-test-từng-phần)
8. [Checklist hoàn thành Phase 2](#8-checklist-hoàn-thành-phase-2)

---

## 1. Tổng quan nghiệp vụ

### Bài toán

Sau Phase 1, hệ thống đã xác minh được metadata cơ bản của một bài báo từ DOI. Nhưng để dùng thực tế tại PTIT, còn thiếu:

- **Tạp chí có uy tín không?** Có trong danh mục SCIE/SSCI/ESCI không? Có predatory/hijacked không? Quartile bao nhiêu?
- **Tác giả khai có thật sự là tác giả bài báo không?** Cần đối chiếu với ORCID hoặc pipeline xử lý tên tiếng Việt.
- **Có dấu hiệu retraction không?** Cần kiểm tra Retraction Watch.
- **Người review xem và xử lý ở đâu?** Cần reviewer queue, audit log để truy vết.

Phase 2 mở rộng PoC thành **MVP nội bộ**: chạy được trên 1 VM PTIT, phục vụ 1 khoa, ~100 bài/tháng, F1 ≥ 0.88.

### Nguyên tắc cốt lõi (giữ từ Phase 1)

- **Grounding trước sinh**: Mọi metadata phải từ API/snapshot chính thống. LLM không được bịa field.
- **Fail safe**: Thiếu evidence → `REVIEW`.
- **Deterministic trước stochastic**: Validation cứng làm trước, LLM chỉ dùng ở decision cuối cùng.

### Nguyên tắc mới trong Phase 2

- **Parallel trước sequential**: Các agent độc lập (metadata, journal, author) chạy song song qua LangGraph fan-out.
- **Cache trước fetch**: DOI đã fetch rồi thì dùng lại 24h (Redis). Snapshot offline (MJL, SCImago) được seed định kỳ.
- **Audit mọi thứ**: Mọi decision, override, review đều ghi WORM log (HMAC chain) — không thể sửa/xóa sau khi ghi.
- **Observability từ đầu**: Langfuse tracing cho LLM call, Prometheus metrics cho throughput/latency/error rate.

### Luồng Phase 2

```
Người dùng gửi DOI + user_claimed_author + user_claimed_affiliation
       │
       ▼
   Validate input (DOI format, required fields)
       │
       ▼
   Kiểm tra Redis cache ──→ Cache hit? ──→ Dùng CMS cũ (nếu < 24h)
       │                                        │
       │ Cache miss                              │
       ▼                                        │
   Router Agent (LangGraph fan-out)              │
       │                                        │
       ├──→ Metadata Agent (Crossref → OpenAlex) │
       ├──→ Journal Agent  (MJL + SCImago + DOAJ + Beall + Hijack)  
       └──→ Author Agent   (ORCID lookup + Vietnamese AND)
       │                                        │
       ▼                                        │
   Aggregator Agent — gom kết quả từ 3 agent     │
       │                                        │
       ▼                                        │
   Decision Agent (LLM với CoVe + Self-Consistency k=3)
       │                                        │
       ├──→ confidence ≥ τ_high (0.90) → APPROVE auto
       ├──→ τ_low (0.65) ≤ confidence < τ_high → REVIEW queue
       └──→ confidence < τ_low → REJECT
       │                                        │
       ▼                                        │
   Lưu DB: Submission + Publication + JournalCheck + AuthorCheck + Decision
       │                                        │
       ▼                                        │
   Ghi Audit Log (WORM)                         │
       │                                        │
       ▼                                        │
   Trả JSON response (có evidence_panel đầy đủ)
```

### Confidence Score Formula (Phase 2)

```
confidence_raw = (
  0.25 × metadata_score     # Crossref/OpenAlex consistency
  0.25 × journal_score      # Indexing + quartile + not predatory
  0.30 × author_score       # ORCID hoặc AND match
  0.10 × retraction_score   # Retraction Watch check
  0.10 × policy_score       # Phù hợp quy chế PTIT
)
confidence_calibrated = sigmoid(A × confidence_raw + B)  # Platt scaling calibrated
```

---

## 2. Khác biệt chính so với Phase 1

| Khía cạnh | Phase 1 PoC | Phase 2 MVP |
|-----------|-------------|-------------|
| **Orchestration** | Sequential (graph.py) | LangGraph parallel fan-out |
| **Agents** | 2 agents (metadata, decision) | 5 agents (router, metadata, journal, author, decision) |
| **Connectors** | Crossref, OpenAlex | + DOAJ, ORCID, ROR, RetractionWatch |
| **Snapshots** | Không có | MJL, SCImago, Beall offline DB |
| **Cache** | Không | Redis DOI cache 24h TTL |
| **Task queue** | Đồng bộ trong request | Celery async tasks |
| **Audit** | Không | WORM audit log (HMAC chain) |
| **Observability** | Không | Langfuse tracing + Prometheus metrics |
| **Reviewer** | Không | Reviewer queue + HITL endpoints |
| **Migration** | `create_all` thô | Alembic migration |
| **Deploy** | Local uvicorn | Docker Compose trên VM |
| **LLM** | 1 prompt, rule-based fallback | CoVe + Self-Consistency k=3, Platt scaling calibrated |
| **CMS** | 8 fields cơ bản | CMS v2.0: journal index, author ORCID/ROR, retraction |
| **F1 target** | ≥ 0.80 | ≥ 0.88 |
| **Latency** | < 10s | < 15s (parallel bù cho work nhiều hơn) |
| **Cost** | < 0.10 USD/bài | ≤ 0.05 USD/bài |

---

## 3. Cách chạy toàn bộ Phase 2

### Yêu cầu hệ thống

- Python 3.12+
- Docker Desktop (cho PostgreSQL, Redis, Celery worker)
- Git
- ORCID API credentials (sandbox OK cho dev)
- 4GB RAM trống (cho PostgreSQL + Redis + worker)

### Bước 1: Clone và cài đặt

```bash
git clone <repo-url>
cd V.A.S.P
git checkout phase2-mvp  # branch riêng cho Phase 2

python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -e ".[dev]"
```

### Bước 2: Cấu hình môi trường

```bash
cp .env.example .env
```

Các biến mới trong Phase 2:

| Biến | Ý nghĩa | Mặc định |
|------|---------|----------|
| `REDIS__URL` | Redis connection string | `redis://localhost:6379/0` |
| `ORCID__CLIENT_ID` | ORCID API client ID | *(rỗng — sandbox)* |
| `ORCID__CLIENT_SECRET` | ORCID API secret | *(rỗng)* |
| `SNAPSHOT__MJL_PATH` | Đường dẫn MJL CSV | `snapshots/mjl_current.csv` |
| `SNAPSHOT__SCIMAGO_PATH` | Đường dẫn SCImago CSV | `snapshots/scimago_jcr.csv` |
| `CELERY__BROKER_URL` | Celery broker | `redis://localhost:6379/1` |
| `AUDIT__SECRET_KEY` | HMAC secret cho WORM log | *(tự sinh nếu trống)* |
| `LLM__SELF_CONSISTENCY_K` | Số lần sample cho Self-Consistency | `3` |
| `LLM__COVE_ENABLED` | Bật CoVe verification | `true` |
| `THRESHOLD__AUTO_APPROVE` | Ngưỡng auto-approve | `0.90` |
| `THRESHOLD__AUTO_REJECT` | Ngưỡng auto-reject | `0.65` |

### Bước 3: Khởi động infrastructure

```bash
# Khởi động PostgreSQL + Redis + Celery worker
docker compose -f docker/docker-compose.yml up -d

# Kiểm tra
docker compose -f docker/docker-compose.yml ps
# Phải thấy: postgres (running), redis (running), celery-worker (running)
```

### Bước 4: Seed snapshots

```bash
# Tải và seed MJL, SCImago, Beall, DOAJ snapshots
python scripts/seed_snapshots.py --all

# Output:
# MJL: 22,000+ journals loaded
# SCImago: 28,000+ journals loaded
# DOAJ: 19,000+ journals loaded
# Beall: 1,300+ journals loaded
```

### Bước 5: Migration database

```bash
# Tạo bảng mới (Alembic)
alembic upgrade head

# Output:
# INFO  [alembic] Running upgrade ... -> 002_phase2_journal_author
```

### Bước 6: Chạy server

```bash
# Terminal 1: FastAPI
uvicorn reviewagent.api.main:app --reload --port 8000

# Terminal 2: Celery worker (nếu tách riêng)
celery -A reviewagent.tasks.celery_app worker --loglevel=info
```

### Bước 7: Gọi API test

#### Submit với đầy đủ thông tin tác giả

```bash
curl -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "doi": "10.1109/5.771073",
    "user_claimed_author": "Nguyen Van A",
    "user_claimed_affiliation": "PTIT"
  }'
```

Response (ví dụ):
```json
{
  "submission_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "COMPLETED",
  "decision_id": "a1b2c3d4-58cc-4372-a567-0e02b2c3d480",
  "decision": "APPROVE",
  "confidence_raw": 0.91,
  "confidence_calibrated": 0.93,
  "evidence_panel": [
    {
      "agent": "metadata",
      "source": "crossref",
      "score": 0.90,
      "detail": "Title, authors, journal match Crossref record"
    },
    {
      "agent": "journal",
      "source": "mjl+scimago",
      "score": 0.85,
      "detail": "SCIE Q1, SJR 2023: 2.1, not predatory"
    },
    {
      "agent": "author",
      "source": "fuzzy_match",
      "score": 0.70,
      "detail": "AND match: Nguyen Van A ~ Nguyen V. A. (score 0.89)"
    }
  ]
}
```

#### Reviewer endpoints

```bash
# Lấy danh sách bài cần review
curl http://localhost:8000/reviews?status=pending

# Reviewer ra quyết định thủ công
curl -X POST http://localhost:8000/reviews/{review_id}/decide \
  -H "Content-Type: application/json" \
  -d '{"decision": "APPROVE", "reviewer_note": "Verified author identity via ORCID"}'
```

### Bước 8: Dừng hệ thống

```bash
docker compose -f docker/docker-compose.yml down
```

---

## 4. Sơ đồ luồng dữ liệu

```
                              ┌─────────────────────────┐
                              │     HTTP Request          │
                              │  POST /submissions       │
                              │  {doi, author, affil}    │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  api/routers/            │
                              │  submissions.py          │
                              │  - Validate input         │
                              │  - Tạo Submission record  │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  cache/redis_client.py   │
                              │  - Kiểm tra DOI cache     │
                              │  - Hit → skip fetch       │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  agents/graph.py         │
                              │  LangGraph StateGraph     │
                              │                          │
                              │  ┌────────────────────┐  │
                              │  │ agents/             │  │
                              │  │ router_agent.py     │  │
                              │  │ → Fan-out 3 nhánh   │  │
                              │  └────────┬───────────┘  │
                              │           │              │
                              │  ┌────────┼───────────┐  │
                              │  │        │           │  │
                              │  ▼        ▼           ▼  │
                              │  ┌────┐ ┌────┐ ┌──────┐  │
                              │  │Meta│ │Jour│ │Author│  │
                              │  │data │ │nal │ │      │  │
                              │  │Agent│ │Agt │ │Agent │  │
                              │  └──┬─┘ └──┬─┘ └──┬───┘  │
                              │     │      │       │      │
                              │  ┌──┴──────┴───────┴──┐   │
                              │  │ agents/             │   │
                              │  │ aggregator_agent.py │   │
                              │  │ → Gom sub-scores    │   │
                              │  └────────┬───────────┘   │
                              │           │               │
                              │  ┌────────▼───────────┐   │
                              │  │ agents/             │   │
                              │  │ decision_agent.py   │   │
                              │  │ → CoVe + SC k=3     │   │
                              │  └────────┬───────────┘   │
                              └───────────┼──────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  DB Layer                │
                              │                          │
                              │  db/repositories/        │
                              │  - submission_repo.py    │
                              │  - decision_repo.py      │
                              │  - journal_repo.py       │
                              │                          │
                              │  db/models/              │
                              │  - submission.py         │
                              │  - publication.py        │
                              │  - decision.py           │
                              │  - journal.py            │
                              │  - audit_log.py          │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  audit/worm_logger.py    │
                              │  - Ghi audit entry       │
                              │  - HMAC chain verify     │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  observability/          │
                              │  - tracing.py (Langfuse) │
                              │  - metrics.py (Prom)     │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  HTTP Response           │
                              │  {submission_id,         │
                              │   decision, confidence,  │
                              │   evidence_panel}        │
                              └─────────────────────────┘
```

### Dependency graph giữa các modules (Phase 2 mở rộng)

```
config.py  ◄──────────────────────────────  mọi module khác đều import
   │
schemas/cms.py         ◄── connectors/*.py, agents/*.py, db/models/*.py
schemas/decision.py    ◄── agents/decision_agent.py, api/routers/decisions.py
schemas/submission.py  ◄── api/routers/submissions.py, db/models/submission.py
schemas/journal.py     ◄── agents/journal_agent.py, snapshots/*.py, db/models/journal.py  [MỚI]
schemas/author.py      ◄── agents/author_agent.py, connectors/orcid.py               [MỚI]
schemas/audit.py       ◄── audit/worm_logger.py, api/routers/reviews.py              [MỚI]
   │
connectors/base.py     ◄── crossref.py, openalex.py, orcid.py, ror.py, doaj.py, retraction_watch.py
   │
snapshots/mjl.py       ◄── agents/journal_agent.py                                   [MỚI]
snapshots/scimago.py   ◄── agents/journal_agent.py                                   [MỚI]
snapshots/beall.py     ◄── agents/journal_agent.py                                   [MỚI]
snapshots/updater.py   ◄── snapshots/*.py                                            [MỚI]
   │
cache/redis_client.py  ◄── agents/metadata_agent.py, api/routers/submissions.py      [MỚI]
   │
db/session.py          ◄── db/models/*.py, db/repositories/*.py, api/deps.py
db/models/*.py         ◄── db/repositories/*.py, api/routers/*.py
db/repositories/*.py   ◄── api/routers/*.py
   │
llm/gateway.py         ◄── agents/decision_agent.py, observability/tracing.py
llm/prompts/*.py       ◄── llm/gateway.py
llm/calibration.py     ◄── llm/gateway.py
   │
agents/state.py        ◄── agents/graph.py
agents/router_agent.py ◄── agents/graph.py                                           [MỚI]
agents/metadata_agent  ◄── agents/graph.py
agents/journal_agent   ◄── agents/graph.py                                           [MỚI]
agents/author_agent    ◄── agents/graph.py                                           [MỚI]
agents/aggregator.py   ◄── agents/graph.py                                           [MỚI]
agents/decision_agent  ◄── agents/graph.py
   │
audit/worm_logger.py   ◄── api/routers/reviews.py, agents/decision_agent.py          [MỚI]
   │
observability/tracing  ◄── llm/gateway.py, api/main.py                               [MỚI]
observability/metrics  ◄── api/main.py                                               [MỚI]
   │
tasks/celery_app.py    ◄── agents/graph.py                                           [MỚI]
tasks/review_task.py   ◄── tasks/celery_app.py, agents/graph.py                      [MỚI]
   │
api/deps.py            ◄── api/routers/*.py
api/routers/*.py       ◄── api/main.py
```

---

## 5. Chi tiết từng file

### 5.1. Layer Schemas — Mở rộng

#### `src/reviewagent/schemas/cms.py` (NÂNG CẤP → v2.0)

**Vai trò**: CMS mở rộng — bổ sung journal indexing, author ORCID/ROR, retraction info.

**Thay đổi so với Phase 1**:

| Field mới | Type | Mô tả |
|-----------|------|-------|
| `abstract` | `str?` | Abstract bài báo (nếu có) |
| `article_type` | `str?` | Loại bài: journal-article, proceedings, book-chapter |
| `language` | `str?` | Ngôn ngữ bài báo |
| `volume` | `str?` | Volume |
| `issue` | `str?` | Issue |
| `pages` | `str?` | Trang |
| `journal.is_scie` | `bool` | Có trong SCIE? |
| `journal.is_ssci` | `bool` | Có trong SSCI? |
| `journal.is_ahci` | `bool` | Có trong AHCI? |
| `journal.is_esci` | `bool` | Có trong ESCI? |
| `journal.is_doaj` | `bool` | Có trong DOAJ? |
| `journal.is_predatory` | `bool?` | Có trong Beall/Cabells? |
| `journal.is_hijacked` | `bool?` | Có bị hijack? |
| `journal.quartile` | `str?` | Q1/Q2/Q3/Q4 theo năm công bố |
| `journal.sjr_value` | `float?` | SCImago SJR value |
| `authors[].orcid` | `str?` | ORCID iD (nếu có) |
| `authors[].affiliation_raw` | `str?` | Tên affiliation thô từ nguồn |
| `authors[].ror_id` | `str?` | ROR ID của affiliation |
| `is_retracted` | `bool` | Đã bị retract? |
| `retraction_doi` | `str?` | DOI của retraction notice |
| `retraction_date` | `date?` | Ngày retraction |
| `cms_version` | `str` | "2.0" |

**Provenance giữ nguyên**: `source_api`, `source_url`, `fetched_at` vẫn bắt buộc.

---

#### `src/reviewagent/schemas/journal.py` (MỚI)

**Vai trò**: Schema cho kết quả kiểm tra tạp chí — output của Journal Agent.

```python
class JournalCheckResult(BaseModel):
    issn_l: str
    title: str
    is_indexed: bool                     # Có trong ít nhất 1 index?
    indexes: list[str]                   # ["SCIE", "SSCI", "ESCI", "DOAJ"]
    quartile_best: str | None            # Q1/Q2/Q3/Q4 — quartile tốt nhất
    sjr_value: float | None              # SCImago SJR
    is_predatory: bool | None            # True nếu có trong Beall/Cabells
    is_hijacked: bool | None             # True nếu journal bị hijack
    flags: list[str]                     # ["NOT_INDEXED", "PREDATORY", "HIJACKED"]
    score: float                         # [0, 1] — tổng hợp điểm journal
    evidence: dict                       # Chi tiết từng nguồn
```

---

#### `src/reviewagent/schemas/author.py` (MỚI)

**Vai trò**: Schema cho kết quả xác minh tác giả — output của Author Agent.

```python
class AuthorCheckResult(BaseModel):
    user_claimed_name: str
    user_claimed_affiliation: str | None
    matched_author: str | None           # Tên tác giả khớp nhất trong bài
    match_method: str                    # "orcid" | "and_exact" | "and_fuzzy" | "none"
    match_score: float                   # [0, 1]
    orcid_verified: bool
    affiliation_match: bool
    flags: list[str]                     # ["NO_AUTHOR_MATCH", "AFFILIATION_MISMATCH"]
    evidence: dict
```

---

#### `src/reviewagent/schemas/audit.py` (MỚI)

**Vai trò**: Schema cho audit log entry — mỗi hành động quan trọng đều ghi 1 entry.

```python
class AuditEntry(BaseModel):
    entry_id: str                        # UUID
    timestamp: datetime
    event_type: str                      # "decision.created" | "review.overridden" | ...
    actor: str                           # "system" | reviewer_id
    submission_id: str
    details: dict                        # Payload chi tiết
    hmac_hash: str                       # HMAC-SHA256 của entry trước + details
    prev_hash: str                       # Hash của entry trước (chain)
```

---

### 5.2. Layer Connectors — Mở rộng

#### `src/reviewagent/connectors/orcid.py` (MỚI)

**Vai trò**: Connector cho ORCID API — xác minh danh tính tác giả.

**Luồng hoạt động**:
```
search_author(name)
  → GET /v3.0/search?q=given-names:...&family-name:...
  → Parse ORCID iD từ kết quả
  → GET /v3.0/{orcid}/works — lấy danh sách công bố
  → So khớp DOI giữa works và submission
  → Return AuthorCheckResult (orcid_verified=true nếu khớp DOI)
```

**Auth**: OAuth 2.0 client credentials (public data — không cần user ủy quyền).

**Rate limit**: 24 requests/second (sandbox), có retry với exponential backoff.

---

#### `src/reviewagent/connectors/ror.py` (MỚI)

**Vai trò**: Connector cho ROR API — chuẩn hóa tên affiliation.

**Luồng hoạt động**:
```
lookup(affiliation_name)
  → GET /v1/organizations?affiliation={name}
  → Parse ROR ID + tên chuẩn
  → Return (ror_id, normalized_name)
```

**Endpoint**: `https://api.ror.org/v1/organizations`

---

#### `src/reviewagent/connectors/retraction_watch.py` (MỚI)

**Vai trò**: Connector cho Retraction Watch database — kiểm tra retraction status.

**Luồng hoạt động**:
```
check_retraction(doi)
  → GET /api/retractions?doi={doi}
  → Return RetractionInfo(retracted=True/False, retraction_doi, retraction_date, reason)
```

**Alternative**: Dùng snapshot CSV offline để tránh rate limit.

---

#### `src/reviewagent/connectors/doaj.py` (MỚI)

**Vai trò**: Connector cho DOAJ API — kiểm tra journal có trong whitelist Open Access không.

**Luồng hoạt động**:
```
check_journal(issn_l)
  → GET /api/v2/search/journals/issn:{issn_l}
  → Return {in_doaj: bool, apc: float?, seal: bool}
```

---

### 5.3. Layer Snapshots (MỚI HOÀN TOÀN)

#### `src/reviewagent/snapshots/mjl.py` (MỚI)

**Vai trò**: Quản lý Master Journal List (MJL) snapshot — nguồn kiểm tra indexing SCIE/SSCI/AHCI/ESCI.

**Dữ liệu**: CSV từ Web of Science, ~22,000 journals.

**Cấu trúc**:
```python
class MJLSnapshot:
    def load(path: str) -> None:
        """Đọc CSV vào memory (dict[issn_l, MJLEntry])"""

    def lookup(issn_l: str) -> MJLEntry | None:
        """Tra cứu O(1) theo ISSN-L"""

@dataclass
class MJLEntry:
    issn_l: str
    title: str
    is_scie: bool
    is_ssci: bool
    is_ahci: bool
    is_esci: bool
```

**Pattern**: Snapshot load khi app startup, dùng `@lru_cache` để tránh reload. Dữ liệu không thay đổi thường xuyên (cập nhật monthly).

---

#### `src/reviewagent/snapshots/scimago.py` (MỚI)

**Vai trò**: Quản lý SCImago SJR snapshot — cung cấp quartile và SJR value theo năm.

**Dữ liệu**: CSV từ SCImago, ~28,000 journals.

```python
class SCImagoSnapshot:
    def lookup(issn_l: str, year: int) -> SCImagoEntry | None:
        """Tra SJR theo ISSN-L và năm công bố"""

@dataclass
class SCImagoEntry:
    issn_l: str
    year: int
    sjr_value: float
    quartile: str  # Q1/Q2/Q3/Q4
```

---

#### `src/reviewagent/snapshots/beall.py` (MỚI)

**Vai trò**: Quản lý Beall's List snapshot — danh sách tạp chí predatory.

**Dữ liệu**: CSV ~1,300 journals.

```python
class BeallSnapshot:
    def is_predatory(issn_l: str, title: str) -> bool:
        """Kiểm tra ISSN hoặc title có trong danh sách không"""
```

---

#### `src/reviewagent/snapshots/updater.py` (MỚI)

**Vai trò**: Scheduled updater — tải snapshot mới từ nguồn định kỳ.

**Cơ chế**: Celery Beat task, chạy monthly.

```python
@celery_app.task
def update_all_snapshots():
    """Tải MJL, SCImago, Beall CSV mới → replace file cũ → reload vào memory"""
```

---

### 5.4. Layer Agents — Mở rộng

#### `src/reviewagent/agents/state.py` (NÂNG CẤP)

**Vai trò**: ReviewState mở rộng — chứa kết quả từ tất cả 5 agent.

```python
class ReviewState(TypedDict):
    submission_id: str
    doi: str
    user_claimed_author: str | None
    user_claimed_affiliation: str | None

    # L1: Identity & Source
    cms: CanonicalMetadataSchema | None

    # L2: Journal Quality
    journal_result: JournalCheckResult | None

    # L3: Author & Affiliation
    author_result: AuthorCheckResult | None

    # L5: Decision
    decision: DecisionResult | None

    # Meta
    errors: list[str]
    metadata_source: str | None
    prompt_version: str
    timing: dict[str, float]  # timing mỗi agent
```

---

#### `src/reviewagent/agents/router_agent.py` (MỚI)

**Vai trò**: Router agent — quyết định những agent nào cần chạy, fan-out song song.

**Logic**:
```python
class RouterAgent:
    def route(self, state: ReviewState) -> list[str]:
        targets = ["metadata"]  # Luôn chạy

        # Chỉ chạy journal agent nếu có ISSN-L trong metadata
        if state.get("cms") and state["cms"].journal.issn_l:
            targets.append("journal")

        # Chỉ chạy author agent nếu user khai báo tên
        if state.get("user_claimed_author"):
            targets.append("author")

        return targets
```

**Cơ chế**: LangGraph `Send` API — gửi state tới các agent đích song song.

---

#### `src/reviewagent/agents/journal_agent.py` (MỚI)

**Vai trò**: **Layer 2** — Kiểm tra chất lượng tạp chí từ snapshots offline.

**Luồng xử lý**:
```
run(cms)
  1. Lấy ISSN-L từ CMS journal
  2. Tra MJL snapshot → is_scie, is_ssci, is_ahci, is_esci
  3. Tra SCImago snapshot theo ISSN-L + pub_year → quartile, SJR
  4. Tra DOAJ connector → is_doaj
  5. Tra Beall snapshot → is_predatory
  6. Tra Hijacked Journal list → is_hijacked
  7. Tính score:
     - indexed (SCIE/SSCI/AHCI): +0.5
     - ESCI/DOAJ: +0.3
     - predatory: score = 0.0
     - hijacked: score = 0.0
     - Q1: +0.3, Q2: +0.2, Q3: +0.1, Q4: 0.0
  8. Build flags nếu có vấn đề
  9. Return JournalCheckResult
```

**Flags ví dụ**: `NOT_INDEXED`, `PREDATORY`, `HIJACKED`, `LOW_QUARTILE`

---

#### `src/reviewagent/agents/author_agent.py` (MỚI)

**Vai trò**: **Layer 3** — Xác minh người khai có thực sự là tác giả bài báo.

**Luồng xử lý (2 đường)**:

**Đường 1 — ORCID (nếu tác giả có ORCID trong CMS)**:
```
1. Duyệt authors[] trong CMS, tìm author có ORCID iD
2. Gọi ORCID API lấy works của author đó
3. So khớp DOI submission với danh sách works
4. Nếu khớp → AuthorCheckResult(match_method="orcid", score=1.0)
```

**Đường 2 — AND Pipeline tiếng Việt (nếu không có ORCID)**:
```
1. Chuẩn hóa tên user khai: Unicode NFC → strip title (TS., PGS., etc.) → lowercase
2. Chuẩn hóa tên từng author trong CMS
3. So khớp:
   a. Exact match sau normalize → score 1.0
   b. Fuzzy match (Levenshtein ratio) → score [0, 1]
   c. Name permutation match: "Nguyen Van A" ↔ "A. V. Nguyen" ↔ "Nguyen V. A."
4. Affiliation match: so sánh affiliation user khai với CMS affiliation
   (dùng ROR normalization nếu có)
5. Return AuthorCheckResult với match_score
```

**Các file hỗ trợ trong `author_nd/`**:

| File | Vai trò |
|------|---------|
| `author_nd/vietnamese.py` | Unicode NFC, diacritics restore, title stripping |
| `author_nd/embeddings.py` | PhoGPT-4B embedding cho semantic name matching (fallback nếu fuzzy fail) |
| `author_nd/disambiguation.py` | Pipeline AND đầy đủ: normalize → candidate generation → scoring → best match |

---

#### `src/reviewagent/agents/aggregator_agent.py` (MỚI)

**Vai trò**: Gom kết quả từ 3 agent song song, tính sub-scores cho decision agent.

**Luồng xử lý**:
```
aggregate(state)
  1. Đọc cms → tính metadata_score
  2. Đọc journal_result → tính journal_score
  3. Đọc author_result → tính author_score
  4. Đọc retraction status → tính retraction_score
  5. Gom flags từ tất cả agent
  6. Gom evidence_panel
  7. Cập nhật state với aggregated scores
```

---

#### `src/reviewagent/agents/decision_agent.py` (NÂNG CẤP)

**Vai trò**: Decision agent nâng cấp — dùng CoVe + Self-Consistency thay vì single inference.

**Hai kỹ thuật mới**:

**CoVe (Chain-of-Verification)**:
```
1. LLM sinh decision ban đầu (có rationale + confidence)
2. LLM tự verify từng claim trong rationale:
   - "Claim: Journal is Q1" → Check: "Does journal_result.quartile_best == Q1?"
   - "Claim: Author has ORCID" → Check: "Does author_result.orcid_verified == True?"
3. Nếu claim nào không khớp → điều chỉnh confidence xuống
4. Trả decision sau verification
```

**Self-Consistency (k=3)**:
```
1. Chạy LLM 3 lần (temperature > 0) → 3 decisions
2. Majority vote cho decision label
3. Confidence = trung bình 3 confidence_calibrated
4. Rationale = rationale của sample có confidence gần nhất với trung bình
```

**Cấu trúc code**:
```python
class DecisionAgent:
    async def run(self, state: ReviewState) -> DecisionResult:
        for attempt in range(3):  # Retry loop
            try:
                if settings.llm.cove_enabled:
                    result = await self._run_cove(state)
                else:
                    result = await self._run_self_consistency(state, k=settings.llm.self_consistency_k)
                return result
            except Exception as e:
                if attempt == 2:
                    return self._rule_based_decision(state)  # Fallback
                await asyncio.sleep(2 ** attempt)
```

**Ngưỡng auto-approve/reject**:
- `confidence_calibrated >= 0.90` → `APPROVE` (auto)
- `0.65 <= confidence_calibrated < 0.90` → `REVIEW` (vào queue)
- `confidence_calibrated < 0.65` → `REJECT` (auto)

---

#### `src/reviewagent/agents/graph.py` (NÂNG CẤP → LangGraph)

**Vai trò**: Orchestrator chuyển từ sequential sang **LangGraph StateGraph fan-out**.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

def build_graph() -> StateGraph:
    builder = StateGraph(ReviewState)

    builder.add_node("router", router_agent.run)
    builder.add_node("metadata_agent", metadata_agent.run)
    builder.add_node("journal_agent", journal_agent.run)
    builder.add_node("author_agent", author_agent.run)
    builder.add_node("aggregator", aggregator_agent.run)
    builder.add_node("decision_agent", decision_agent.run)

    builder.add_edge(START, "router")

    # Fan-out từ router → 3 agent song song
    builder.add_conditional_edges(
        "router",
        lambda state: [Send("metadata_agent", state),
                       Send("journal_agent", state),
                       Send("author_agent", state)],
    )

    # Tất cả cùng về aggregator
    builder.add_edge("metadata_agent", "aggregator")
    builder.add_edge("journal_agent", "aggregator")
    builder.add_edge("author_agent", "aggregator")

    builder.add_edge("aggregator", "decision_agent")
    builder.add_edge("decision_agent", END)

    return builder.compile()
```

**Điểm quan trọng**:
- Router kiểm tra điều kiện trước khi fan-out (không cần gọi agent nếu không có dữ liệu).
- Các agent chạy độc lập — không share mutable state trực tiếp (chỉ đọc state).
- Aggregator là barrier: chờ cả 3 agent xong mới tiếp tục.
- LangGraph cung cấp retry, timeout, checkpointing built-in.

---

### 5.5. Layer LLM — Mở rộng

#### `src/reviewagent/llm/prompts/decision_v2.py` (MỚI)

**Vai trò**: Prompt v2 cho decision với CoVe — yêu cầu model tự verify claims.

**Khác biệt với v1**:
- System prompt yêu cầu model liệt kê evidence cho từng claim.
- User prompt chứa đầy đủ sub-scores từ aggregator.
- Output schema có thêm `verification_checks` field.

#### `src/reviewagent/llm/prompts/metadata_v1.py` (MỚI)

**Vai trò**: Prompt chuẩn hóa metadata khi cả Crossref và OpenAlex đều thiếu.

#### `src/reviewagent/llm/calibration.py` (NÂNG CẤP)

**Vai trò**: Platt scaling thực thụ — không còn là identity function.

```python
def calibrate_confidence(raw: float) -> float:
    """Platt scaling: sigmoid(A * raw + B)"""
    A = 2.5   # Slope (từ training data)
    B = -1.0  # Intercept
    return 1.0 / (1.0 + math.exp(-(A * raw + B)))
```

**Training**: Dùng gold dataset 100 bài đã annotated để fit A, B qua logistic regression.

---

### 5.6. Layer Cache (MỚI)

#### `src/reviewagent/cache/redis_client.py` (MỚI)

**Vai trò**: Redis client — cache DOI metadata 24h, cache snapshot lookups.

```python
class RedisCache:
    async def get_cms(self, doi: str) -> CanonicalMetadataSchema | None: ...
    async def set_cms(self, doi: str, cms: CanonicalMetadataSchema, ttl: int = 86400): ...
    async def invalidate(self, doi: str): ...
```

**Key pattern**: `cms:{doi_hash}` → JSON serialized CMS.

**Sử dụng trong Metadata Agent**: Trước khi gọi Crossref, kiểm tra cache. Nếu cache hit → skip API call.

---

### 5.7. Layer Tasks (MỚI)

#### `src/reviewagent/tasks/celery_app.py` (MỚI)

**Vai trò**: Celery app factory — cấu hình broker (Redis), backend, task routes.

```python
from celery import Celery

app = Celery("reviewagent")
app.config_from_object("reviewagent.config.CeleryConfig")
```

#### `src/reviewagent/tasks/review_task.py` (MỚI)

**Vai trò**: Celery task chạy pipeline bất đồng bộ.

```python
@app.task(bind=True, max_retries=3)
def run_review_pipeline(self, submission_id: str, doi: str):
    """Chạy toàn bộ pipeline trong background worker"""
    async def _run():
        async with AsyncSessionLocal() as db:
            pipeline = ReviewPipeline()
            state = await pipeline.run(submission_id, doi, db)
            # Lưu kết quả, gửi notification...
```

**Lợi ích**: Không block HTTP request nếu pipeline lâu (>10s). Client nhận `status: PROCESSING` rồi poll decision sau.

#### `src/reviewagent/tasks/snapshot_task.py` (MỚI)

**Vai trò**: Celery Beat task — cập nhật snapshot định kỳ.

---

### 5.8. Layer Audit (MỚI)

#### `src/reviewagent/audit/worm_logger.py` (MỚI)

**Vai trò**: Write-Once-Read-Many audit log — mỗi entry được chain bằng HMAC-SHA256.

**Cơ chế WORM**:
```
Entry 1: HMAC(secret, payload1) → hash1
Entry 2: HMAC(secret, payload2 + hash1) → hash2
Entry 3: HMAC(secret, payload3 + hash2) → hash3
```

Nếu ai sửa Entry 2 → hash2 thay đổi → hash3 không khớp → phát hiện tampering.

```python
class WORMLogger:
    def __init__(self, secret_key: str):
        self._key = secret_key.encode()

    def write(self, event_type: str, actor: str, submission_id: str, details: dict) -> AuditEntry:
        prev_hash = self._get_last_hash()
        payload = json.dumps({"event_type": event_type, "actor": actor, ...})
        hmac_hash = hmac.new(self._key, (payload + prev_hash).encode(), hashlib.sha256).hexdigest()
        entry = AuditEntry(..., hmac_hash=hmac_hash, prev_hash=prev_hash)
        self._persist(entry)
        return entry

    def verify_chain(self) -> bool:
        """Kiểm tra toàn bộ chain không bị tamper"""
```

**Events được ghi**:
- `decision.created` — Mỗi khi decision agent chạy
- `review.overridden` — Khi reviewer sửa decision
- `submission.created` — Khi user gửi submission mới
- `appeal.filed` — Khi có kháng nghị (Phase 3)

---

### 5.9. Layer Database — Mở rộng

#### `src/reviewagent/db/models/journal.py` (MỚI)

**Vai trò**: Bảng `journal_checks` — cache kết quả kiểm tra tạp chí.

| Column | Type | Mô tả |
|--------|------|-------|
| `id` | UUID PK | ID |
| `publication_id` | UUID FK | Liên kết publication |
| `issn_l` | String(32) | ISSN-L đã kiểm tra |
| `indexes` | JSONB | Danh sách index |
| `quartile_best` | String(8) | Quartile tốt nhất |
| `sjr_value` | Float | SJR value |
| `is_predatory` | Boolean | Predatory? |
| `is_hijacked` | Boolean | Hijacked? |
| `score` | Float | Tổng điểm |
| `evidence` | JSONB | Chi tiết từng nguồn |

#### `src/reviewagent/db/models/audit_log.py` (MỚI)

**Vai trò**: Bảng `audit_log` — lưu WORM audit entries.

| Column | Type | Mô tả |
|--------|------|-------|
| `id` | UUID PK | ID |
| `sequence` | Integer | Số thứ tự tăng dần |
| `timestamp` | DateTime | Thời điểm ghi |
| `event_type` | String(64) | Loại sự kiện |
| `actor` | String(128) | Ai thực hiện |
| `submission_id` | UUID FK | Submission liên quan |
| `details` | JSONB | Payload |
| `hmac_hash` | String(128) | HMAC-SHA256 hash |
| `prev_hash` | String(128) | Hash của entry trước |

#### `src/reviewagent/db/repositories/journal_repo.py` (MỚI)

**Vai trò**: CRUD cho journal_checks.

---

### 5.10. Layer API — Mở rộng

#### `src/reviewagent/api/routers/reviews.py` (MỚI)

**Vai trò**: HITL reviewer endpoints.

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/reviews` | GET | Danh sách bài cần review (status=REVIEW, phân trang) |
| `/reviews/{review_id}` | GET | Chi tiết 1 bài trong queue |
| `/reviews/{review_id}/decide` | POST | Reviewer ra quyết định thủ công |
| `/reviews/{review_id}/assign` | POST | Assign reviewer cho bài |
| `/reviews/stats` | GET | Thống kê: pending, done hôm nay, avg response time |

**Override workflow**:
```
1. Decision agent trả REVIEW
2. Submission vào review queue
3. Reviewer xem evidence_panel → ra quyết định APPROVE/REJECT
4. Audit log ghi: review.overridden
5. Decision cuối cùng = quyết định của reviewer
```

#### `src/reviewagent/api/middleware.py` (MỚI)

**Vai trò**: Middleware — auth (JWT/SAML SSO), CORS, request logging.

```python
async def auth_middleware(request: Request, call_next):
    """Verify JWT token từ PTIT SSO"""
    ...

async def request_logging_middleware(request: Request, call_next):
    """Log mỗi request: method, path, duration, status"""
    ...
```

---

### 5.11. Layer Observability (MỚI)

#### `src/reviewagent/observability/tracing.py` (MỚI)

**Vai trò**: Langfuse tracing — ghi lại mọi LLM call để debug và audit prompt.

```python
from langfuse import Langfuse

langfuse = Langfuse()

@contextmanager
def trace_llm_call(agent_name: str, prompt_version: str, input_data: dict):
    trace = langfuse.trace(name=f"{agent_name}.{prompt_version}")
    yield trace
    trace.update(output=...)  # Ghi kết quả sau khi LLM trả về
```

**Metric tracked**:
- Latency mỗi LLM call
- Token usage (input/output)
- Cost per call
- Success/failure rate

#### `src/reviewagent/observability/metrics.py` (MỚI)

**Vai trò**: Prometheus metrics — throughput, error rate, decision distribution.

```python
from prometheus_client import Counter, Histogram, Gauge

submission_counter = Counter("reviewagent_submissions_total", "...")
decision_histogram = Histogram("reviewagent_decision_duration_seconds", "...")
pending_gauge = Gauge("reviewagent_reviews_pending", "...")
```

**Endpoint**: `GET /metrics` — Prometheus scrape target.

---

### 5.12. Scripts — Mở rộng

#### `scripts/seed_snapshots.py` (MỚI)

**Vai trò**: Tải và seed tất cả snapshots vào DB.

```bash
python scripts/seed_snapshots.py --all
python scripts/seed_snapshots.py --mjl --scimago  # Riêng lẻ
```

#### `scripts/eval.py` (NÂNG CẤP)

**Vai trò**: Evaluation với gold dataset 100 bài — tính F1 trên decision label.

```bash
python scripts/eval.py --dataset tests/gold_dataset/seed_100.json --output eval_report.json
```

---

## 6. Thứ tự code và dependency

### Giai đoạn 1: Chuẩn bị hạ tầng (files 1-4)

```
1. Cập nhật pyproject.toml
   → Thêm dependencies: langgraph, celery, redis, prometheus-client, langfuse, alembic

2. Cập nhật .env.example
   → Thêm biến mới: REDIS, ORCID, CELERY, THRESHOLD, SNAPSHOT, AUDIT

3. Cập nhật docker/docker-compose.yml
   → Thêm Redis, Celery worker, Celery beat services

4. Cập nhật config.py
   → Thêm RedisSettings, ORCIDSettings, CelerySettings, ThresholdSettings, AuditSettings
```

### Giai đoạn 2: Schemas mở rộng (files 5-8)

```
5. schemas/journal.py
   → Không phụ thuộc file khác (chỉ Pydantic)
   → Định nghĩa JournalCheckResult

6. schemas/author.py
   → Không phụ thuộc file khác
   → Định nghĩa AuthorCheckResult

7. schemas/audit.py
   → Không phụ thuộc file khác
   → Định nghĩa AuditEntry

8. Nâng cấp schemas/cms.py → v2.0
   → Thêm fields: journal indexing, author ORCID/ROR, retraction
   → Phụ thuộc: không
```

### Giai đoạn 3: Connectors mới (files 9-12)

```
 9. connectors/orcid.py
    → Phụ thuộc: base.py, schemas/cms.py

10. connectors/ror.py
    → Phụ thuộc: base.py

11. connectors/retraction_watch.py
    → Phụ thuộc: base.py

12. connectors/doaj.py
    → Phụ thuộc: base.py
```

### Giai đoạn 4: Snapshots + Cache + Audit (files 13-18)

```
13. snapshots/mjl.py
    → Phụ thuộc: không (đọc CSV thuần)

14. snapshots/scimago.py
    → Phụ thuộc: không

15. snapshots/beall.py
    → Phụ thuộc: không

16. snapshots/updater.py
    → Phụ thuộc: mjl.py, scimago.py, beall.py

17. cache/redis_client.py
    → Phụ thuộc: config.py, schemas/cms.py

18. audit/worm_logger.py
    → Phụ thuộc: config.py, schemas/audit.py
```

### Giai đoạn 5: Author AND Pipeline (files 19-21)

```
19. author_nd/vietnamese.py
    → Phụ thuộc: không (xử lý string thuần)

20. author_nd/embeddings.py
    → Phụ thuộc: không (PhoGPT model)

21. author_nd/disambiguation.py
    → Phụ thuộc: vietnamese.py, embeddings.py
```

### Giai đoạn 6: Agents mở rộng (files 22-27)

```
22. Nâng cấp agents/state.py
    → Thêm fields: user_claimed_*, journal_result, author_result, timing

23. agents/router_agent.py
    → Phụ thuộc: state.py

24. agents/journal_agent.py
    → Phụ thuộc: snapshots/*.py, connectors/doaj.py, schemas/journal.py

25. agents/author_agent.py
    → Phụ thuộc: connectors/orcid.py, connectors/ror.py, author_nd/*.py, schemas/author.py

26. agents/aggregator_agent.py
    → Phụ thuộc: state.py, schemas/*.py

27. Nâng cấp agents/decision_agent.py → CoVe + Self-Consistency
    → Phụ thuộc: llm/gateway.py, llm/prompts/decision_v2.py

28. Nâng cấp agents/graph.py → LangGraph parallel
    → Phụ thuộc: router, journal, author, aggregator, state.py
```

### Giai đoạn 7: Database mở rộng (files 29-32)

```
29. db/models/journal.py
30. db/models/audit_log.py
31. db/repositories/journal_repo.py
32. Alembic migration scripts
```

### Giai đoạn 8: Tasks + Observability (files 33-38)

```
33. tasks/celery_app.py
34. tasks/review_task.py
35. tasks/snapshot_task.py
36. observability/tracing.py
37. observability/metrics.py
38. Nâng cấp llm/gateway.py → tích hợp Langfuse tracing
```

### Giai đoạn 9: API mở rộng (files 39-42)

```
39. api/middleware.py
40. api/routers/reviews.py
41. Nâng cấp api/deps.py
42. Nâng cấp api/main.py → thêm router reviews, middleware, metrics
```

### Giai đoạn 10: Scripts + Tests + Docs (files 43-48)

```
43. scripts/seed_snapshots.py
44. Nâng cấp scripts/eval.py
45. tests/unit/test_journal_agent.py
46. tests/unit/test_author_agent.py
47. tests/integration/test_review_pipeline.py
48. tests/gold_dataset/seed_100.json
```

---

## 7. Cách test từng phần

### Test 1: Schema mới

```bash
# Test schemas mới (journal, author, audit)
pytest tests/unit/test_schemas.py -v

# Test CMS v2.0 validation
python -c "
from reviewagent.schemas.cms import CanonicalMetadataSchema
# Test retraction fields, journal indexing fields
"
```

### Test 2: Connectors mới

```bash
# Test ORCID (cần sandbox credentials)
python -c "
from reviewagent.connectors.orcid import ORCIDConnector
# Test với ORCID sandbox
"

# Test ROR
curl "https://api.ror.org/v1/organizations?affiliation=Posts+and+Telecommunications+Institute+of+Technology"
```

### Test 3: Snapshots

```bash
# Seed và test snapshot lookup
python scripts/seed_snapshots.py --mjl --scimago

python -c "
from reviewagent.snapshots.mjl import MJLSnapshot
s = MJLSnapshot()
s.load('snapshots/mjl_current.csv')
print(s.lookup('0018-9448'))  # IEEE Trans Info Theory → SCIE
"
```

### Test 4: Journal Agent

```bash
python -c "
from reviewagent.agents.journal_agent import JournalAgent
# Test với DOI có ISSN-L
"
```

### Test 5: AND Pipeline

```bash
python -c "
from reviewagent.author_nd.vietnamese import normalize_vietnamese_name
print(normalize_vietnamese_name('Nguyễn Văn A'))
# → 'nguyen van a'
"
```

### Test 6: Audit WORM

```bash
python -c "
from reviewagent.audit.worm_logger import WORMLogger
logger = WORMLogger('test-secret')
e1 = logger.write('decision.created', 'system', 'sub-1', {'decision': 'APPROVE'})
e2 = logger.write('review.overridden', 'reviewer-1', 'sub-1', {'new_decision': 'REJECT'})
print(logger.verify_chain())  # True
"
```

### Test 7: LangGraph Pipeline

```bash
python -c "
from reviewagent.agents.graph import build_graph
graph = build_graph()
result = graph.invoke({'submission_id': '...', 'doi': '10.1109/5.771073'})
print(result['decision'])
"
```

### Test 8: API endpoints

```bash
# Health check
curl http://localhost:8000/health

# Metrics (Prometheus)
curl http://localhost:8000/metrics

# Reviewer queue
curl http://localhost:8000/reviews?status=pending

# Assign + decide
curl -X POST http://localhost:8000/reviews/{id}/decide \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{"decision": "APPROVE", "reviewer_note": "Verified"}'
```

### Test 9: Full Eval

```bash
python scripts/eval.py --dataset tests/gold_dataset/seed_100.json --phase2
# Output:
# Precision: 0.90
# Recall: 0.87
# F1: 0.885
# Cost/bài: 0.043 USD
# Latency avg: 8.2s
```

---

## 8. Checklist hoàn thành Phase 2

### Infrastructure
- [ ] Docker Compose có PostgreSQL + Redis + Celery worker + Celery beat
- [ ] Alembic migration thay thế `create_all`
- [ ] `.env` có đầy đủ biến Phase 2
- [ ] `config.py` có tất cả Settings mới

### Schemas
- [ ] `schemas/cms.py` v2.0 — journal indexing, author ORCID/ROR, retraction
- [ ] `schemas/journal.py` — JournalCheckResult
- [ ] `schemas/author.py` — AuthorCheckResult
- [ ] `schemas/audit.py` — AuditEntry

### Snapshots
- [ ] `snapshots/mjl.py` — MJL lookup SCIE/SSCI/AHCI/ESCI
- [ ] `snapshots/scimago.py` — SCImago lookup quartile/SJR
- [ ] `snapshots/beall.py` — Predatory check
- [ ] `snapshots/updater.py` — Scheduled update
- [ ] `scripts/seed_snapshots.py` — Seed script

### Connectors
- [ ] `connectors/orcid.py` — ORCID search + works
- [ ] `connectors/ror.py` — ROR affiliation
- [ ] `connectors/retraction_watch.py` — Retraction check
- [ ] `connectors/doaj.py` — DOAJ whitelist

### Cache + Audit + AND
- [ ] `cache/redis_client.py` — DOI cache 24h + snapshot cache
- [ ] `audit/worm_logger.py` — WORM audit log với HMAC chain
- [ ] `author_nd/vietnamese.py` — Unicode NFC + name normalization
- [ ] `author_nd/embeddings.py` — PhoGPT embedding
- [ ] `author_nd/disambiguation.py` — Full AND pipeline

### Agents
- [ ] `agents/state.py` nâng cấp — ReviewState mở rộng
- [ ] `agents/router_agent.py` — Điều hướng fan-out
- [ ] `agents/journal_agent.py` — Layer 2
- [ ] `agents/author_agent.py` — Layer 3
- [ ] `agents/aggregator_agent.py` — Gom kết quả
- [ ] `agents/decision_agent.py` nâng cấp — CoVe + SC k=3
- [ ] `agents/graph.py` nâng cấp — LangGraph parallel

### LLM
- [ ] `llm/prompts/decision_v2.py` — Prompt CoVe
- [ ] `llm/prompts/metadata_v1.py` — Prompt chuẩn hóa
- [ ] `llm/calibration.py` nâng cấp — Platt scaling thực thụ
- [ ] `llm/gateway.py` nâng cấp — Tích hợp Langfuse tracing

### Database
- [ ] `db/models/journal.py` — Bảng journal_checks
- [ ] `db/models/audit_log.py` — Bảng audit_log
- [ ] `db/repositories/journal_repo.py` — CRUD journal
- [ ] Alembic migration scripts

### Tasks
- [ ] `tasks/celery_app.py` — Celery app
- [ ] `tasks/review_task.py` — Pipeline async task
- [ ] `tasks/snapshot_task.py` — Snapshot update task

### API
- [ ] `api/middleware.py` — Auth, CORS, logging
- [ ] `api/routers/reviews.py` — Reviewer HITL endpoints
- [ ] `api/deps.py` nâng cấp — Thêm dependencies mới
- [ ] `api/main.py` nâng cấp — Thêm routers, middleware, metrics

### Observability
- [ ] `observability/tracing.py` — Langfuse LLM tracing
- [ ] `observability/metrics.py` — Prometheus metrics

### Tests
- [ ] `tests/unit/test_journal_agent.py` — (≥ 5 tests)
- [ ] `tests/unit/test_author_agent.py` — (≥ 5 tests)
- [ ] `tests/unit/test_worm_logger.py` — (≥ 3 tests)
- [ ] `tests/integration/test_langgraph_pipeline.py` — (≥ 3 tests)
- [ ] `tests/integration/test_reviewer_api.py` — (≥ 3 tests)
- [ ] `tests/gold_dataset/seed_100.json` — 100 bài annotated

### Chỉ số đánh giá
- [ ] F1 ≥ 0.88 trên gold dataset 100 bài
- [ ] Latency trung bình < 15s
- [ ] Cost < 0.05 USD/bài
- [ ] Uptime 99% trên VM PTIT (pilot 1 tháng)

---

## Phụ lục: Câu hỏi thường gặp

**Q: Tại sao chuyển từ sequential sang LangGraph parallel?**
A: Phase 1 chỉ có 2 agent tuần tự. Phase 2 thêm journal agent và author agent — 3 agent này độc lập với nhau (không cần output của nhau). Chạy song song giảm latency từ ~10s xuống ~5-8s dù work nhiều hơn. LangGraph cung cấp retry, timeout, checkpointing built-in.

**Q: Tại sao cần snapshot offline thay vì gọi API real-time?**
A: MJL, SCImago, Beall không có API real-time (hoặc có rate limit rất thấp). Snapshot CSV seed vào memory/DB lúc startup — lookup O(1) — nhanh hơn API call nhiều. Cập nhật monthly qua Celery Beat.

**Q: Redis cache có thực sự cần trong MVP không?**
A: Cần. Cùng 1 DOI có thể được submit nhiều lần (nhiều giảng viên cùng là co-author). Cache 24h tránh gọi lại Crossref/OpenAlex — tiết kiệm cost và tăng tốc. Redis cũng dùng làm Celery broker.

**Q: WORM audit log dùng để làm gì?**
A: Khi có tranh chấp (giảng viên khiếu nại decision), audit log chứng minh hệ thống đã xử lý đúng quy trình, không ai sửa kết quả sau khi lưu. HMAC chain đảm bảo tính toàn vẹn — tương tự blockchain nhưng nhẹ hơn.

**Q: Khi nào dùng Celery thay vì xử lý đồng bộ?**
A: Celery dùng cho batch processing (nhiều submission cùng lúc) hoặc khi pipeline quá 10s. Endpoint vẫn có thể gọi pipeline đồng bộ cho single submission. Celery là infrastructure sẵn sàng cho scale.

**Q: AND pipeline xử lý tên tiếng Việt như thế nào?**
A: 3 bước: (1) Unicode NFC chuẩn hóa dấu, (2) strip học hàm/học vị (TS., PGS., GS.), (3) so khớp exact → fuzzy (Levenshtein) → permutation (đảo thứ tự tên). Nếu vẫn fail, dùng PhoGPT-4B embedding để so semantic similarity.

**Q: Tại sao τ_high = 0.90 trong Phase 2 (cao hơn Phase 1)?**
A: Phase 1 dùng rule-based đơn giản, τ=0.75. Phase 2 có nhiều evidence hơn (journal + author + retraction) → confidence chính xác hơn → có thể nâng ngưỡng auto-approve lên 0.90 để giảm false positive.
