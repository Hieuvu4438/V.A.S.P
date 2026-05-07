# Phase 1 PoC — Hướng dẫn chi tiết

Tài liệu này dành cho developer muốn hiểu toàn bộ Phase 1 PoC của ReviewAgent PTIT: cách chạy, chức năng từng file, thứ tự code, và luồng nghiệp vụ.

---

## Mục lục

1. [Tổng quan nghiệp vụ](#1-tổng-quan-nghiệp-vụ)
2. [Cách chạy toàn bộ Phase 1](#2-cách-chạy-toàn-bộ-phase-1)
3. [Sơ đồ luồng dữ liệu](#3-sơ-đồ-luồng-dữ-liệu)
4. [Chi tiết từng file — vai trò và chức năng](#4-chi-tiết-từng-file)
5. [Thứ tự code và dependency giữa các file](#5-thứ-tự-code-và-dependency)
6. [Cách test từng phần](#6-cách-test-từng-phần)
7. [Checklist hoàn thành Phase 1](#7-checklist-hoàn-thành-phase-1)

---

## 1. Tổng quan nghiệp vụ

### Bài toán

Giảng viên PTIT kê khai công bố khoa học. Hệ thống cần tự động kiểm tra xem công bố đó có thật không, có đáng tin cậy không. Phase 1 giải quyết bài toán cốt lõi nhất: **xác minh metadata (title, authors, journal, date) của một bài báo từ DOI**.

### Nguyên tắc cốt lõi

- **Grounding trước sinh**: Metadata phải lấy từ API chính thống (Crossref, OpenAlex). LLM tuyệt đối không được tự bịa ra DOI, ISSN, year.
- **Fail safe**: Khi thiếu evidence → trả về `REVIEW` thay vì `APPROVE` mù quáng.
- **Deterministic trước stochastic**: Validation cứng (DOI format, date range) làm trước, LLM chỉ dùng để ra decision cuối cùng.

### Luồng Phase 1

```
Người dùng gửi DOI
       │
       ▼
   Validate DOI format (regex)
       │
       ▼
   Gọi Crossref API ──→ Có dữ liệu? ──→ Map vào CMS
       │                                    │
       │ Không                                │
       ▼                                    │
   Gọi OpenAlex API ──→ Có dữ liệu? ──→ Map vào CMS
       │                                    │
       │ Không                                │
       ▼                                    │
   Trả lỗi "không tìm thấy"                │
       │                                    │
       └────────────────────────────────────┘
                       │
                       ▼
              CMS chuẩn hóa (có provenance)
                       │
                       ▼
              Decision Agent
              (LLM nếu có API key,
               rule-based nếu không)
                       │
                       ▼
              APPROVE / REVIEW / REJECT
              + confidence + rationale + flags
                       │
                       ▼
              Lưu vào DB:
              - Submission (input)
              - Publication (CMS cache)
              - Decision (kết quả)
                       │
                       ▼
              Trả JSON response cho client
```

---

## 2. Cách chạy toàn bộ Phase 1

### Yêu cầu hệ thống

- Python 3.12+
- Docker Desktop (cho PostgreSQL dev)
- Git

### Bước 1: Clone và cài đặt

```bash
git clone <repo-url>
cd V.A.S.P

# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (Linux/macOS)
source .venv/bin/activate

# Cài dependencies
pip install -e ".[dev]"
```

### Bước 2: Cấu hình môi trường

```bash
# Copy file mẫu
cp .env.example .env
```

File `.env` mặc định đã đủ để chạy local. Các biến quan trọng:

| Biến | Ý nghĩa | Mặc định |
|------|---------|----------|
| `APP__ENV` | Môi trường (development/production) | `development` |
| `APP__PORT` | Cổng chạy FastAPI | `8000` |
| `DATABASE__URL` | Connection string PostgreSQL | `postgresql+asyncpg://postgres:postgres@localhost:5432/reviewagent` |
| `LLM__API_KEY` | Khóa Anthropic API (để trống nếu chưa có) | *(rỗng)* |
| `LLM__MODEL` | Model sẽ dùng | `claude-opus-4-7` |

> **Quan trọng**: Để trống `LLM__API_KEY` hệ thống vẫn chạy được — sẽ dùng rule-based decision thay vì LLM.

### Bước 3: Khởi động PostgreSQL

```bash
docker compose -f docker/docker-compose.yml up -d
```

Kiểm tra DB đã chạy:

```bash
docker compose -f docker/docker-compose.yml ps
# Phải thấy postgres: "running"
```

### Bước 4: Tạo bảng database

```bash
python scripts/migrate.py upgrade
```

Output mong đợi:
```
Created tables: decisions, publications, submissions
```

### Bước 5: Chạy FastAPI server

```bash
uvicorn reviewagent.api.main:app --reload --port 8000
```

Mở browser: `http://localhost:8000/docs` — giao diện Swagger UI.

### Bước 6: Gọi API test

#### Health check

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok", "database": "ok"}
```

#### Submit một DOI để review

```bash
curl -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -d '{"doi": "10.1109/5.771073"}'
```

Response (ví dụ):
```json
{
  "submission_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "COMPLETED",
  "decision_id": "a1b2c3d4-58cc-4372-a567-0e02b2c3d480"
}
```

#### Xem kết quả decision

```bash
# Theo decision_id
curl http://localhost:8000/decisions/a1b2c3d4-58cc-4372-a567-0e02b2c3d480

# Hoặc theo submission_id
curl "http://localhost:8000/decisions?submission_id=f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

Response:
```json
{
  "decision_id": "a1b2c3d4-58cc-4372-a567-0e02b2c3d480",
  "submission_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "decision": "APPROVE",
  "confidence_raw": 0.9,
  "confidence_calibrated": 0.9,
  "rationale": "Metadata is reasonably complete from an authoritative source.",
  "flags": [],
  "evidence": {
    "sub_scores": {
      "metadata_completeness": 1.0,
      "source_reliability": 0.8
    }
  }
}
```

### Bước 7: Dừng hệ thống

```bash
# Dừng server: Ctrl+C
# Dừng PostgreSQL:
docker compose -f docker/docker-compose.yml down
```

---

## 3. Sơ đồ luồng dữ liệu

```
                          ┌─────────────────────────┐
                          │     HTTP Request         │
                          │  POST /submissions       │
                          │  {"doi": "10.xxx/yyy"}   │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │  api/routers/            │
                          │  submissions.py          │
                          │  - Validate DOI format    │
                          │  - Tạo Submission record  │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │  agents/graph.py         │
                          │  ReviewPipeline.run()    │
                          │                          │
                          │  ┌────────────────────┐  │
                          │  │ agents/             │  │
                          │  │ metadata_agent.py   │  │
                          │  │                     │  │
                          │  │ CrossrefConnector   │  │
                          │  │   └─ connectors/    │  │
                          │  │      crossref.py    │  │
                          │  │      └─ base.py     │  │
                          │  │                     │  │
                          │  │ OpenAlexConnector   │  │
                          │  │   └─ connectors/    │  │
                          │  │      openalex.py    │  │
                          │  │      └─ base.py     │  │
                          │  │                     │  │
                          │  │ → CanonicalMetadata │  │
                          │  │   Schema (CMS)      │  │
                          │  └────────┬───────────┘  │
                          │           │              │
                          │  ┌────────▼───────────┐  │
                          │  │ agents/             │  │
                          │  │ decision_agent.py   │  │
                          │  │                     │  │
                          │  │ LLMGateway          │  │
                          │  │   └─ llm/gateway.py │  │
                          │  │   └─ llm/prompts/   │  │
                          │  │      decision_v1.py │  │
                          │  │   └─ llm/           │  │
                          │  │      calibration.py │  │
                          │  │                     │  │
                          │  │ → DecisionResult    │  │
                          │  └────────┬───────────┘  │
                          └───────────┼─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │  DB Layer                │
                          │                          │
                          │  db/repositories/        │
                          │  - submission_repo.py    │
                          │  - decision_repo.py      │
                          │                          │
                          │  db/models/              │
                          │  - submission.py         │
                          │  - publication.py        │
                          │  - decision.py           │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │  HTTP Response           │
                          │  {submission_id,         │
                          │   status, decision_id}   │
                          └─────────────────────────┘
```

### Dependency graph giữa các modules

```
config.py  ◄──────────────────────────────  mọi module khác đều import
   │
schemas/cms.py  ◄─────────── connectors/*.py, agents/*.py, db/models/*.py
schemas/decision.py  ◄────── agents/decision_agent.py, api/routers/decisions.py
schemas/submission.py  ◄──── api/routers/submissions.py, db/models/submission.py
   │
connectors/base.py  ◄──────── crossref.py, openalex.py
   │
db/session.py  ◄───────────── db/models/*.py, db/repositories/*.py, api/deps.py
db/models/*.py  ◄──────────── db/repositories/*.py, api/routers/submissions.py
db/repositories/*.py  ◄────── api/routers/submissions.py, api/routers/decisions.py
   │
llm/gateway.py  ◄──────────── agents/decision_agent.py
llm/prompts/decision_v1.py ◄─ llm/gateway.py
llm/calibration.py  ◄──────── llm/gateway.py
   │
agents/state.py  ◄─────────── agents/graph.py
agents/metadata_agent.py  ◄── agents/graph.py
agents/decision_agent.py  ◄── agents/graph.py
   │
api/deps.py  ◄─────────────── api/routers/*.py
api/routers/*.py  ◄────────── api/main.py
```

---

## 4. Chi tiết từng file

### 4.1. Layer Foundation

#### `pyproject.toml`
**Vai trò**: Khai báo project metadata, dependencies, và tool config.

**Điểm quan trọng**:
- Build system: `hatchling`
- Dependencies chính: `fastapi`, `pydantic>=2.9`, `sqlalchemy>=2.0`, `httpx`, `uvicorn`
- Dev dependencies: `pytest`, `pytest-asyncio`, `mypy`
- Python yêu cầu: `>=3.12`

#### `.env.example`
**Vai trò**: Template biến môi trường. Copy thành `.env` để dùng thật.

**Cấu trúc nested env**: `APP__ENV`, `DATABASE__URL`, `LLM__API_KEY` — dấu `__` phân cách nested settings (pydantic-settings `env_nested_delimiter`).

#### `src/reviewagent/config.py`
**Vai trò**: Load toàn bộ cấu hình từ env vars, cung cấp singleton `get_settings()`.

**Cấu trúc**:
```python
Settings
  ├── app: AppSettings        # env, name, host, port, log_level
  ├── database: DatabaseSettings  # url (asyncpg)
  ├── apis: APIsSettings      # crossref_base_url, openalex_base_url
  └── llm: LLMSettings        # provider, api_key, model, timeout
```

**Pattern**: `@lru_cache` trên `get_settings()` để settings chỉ load 1 lần.

---

### 4.2. Layer Schemas (Data Contracts)

#### `src/reviewagent/schemas/cms.py`
**Vai trò**: **Canonical Metadata Schema — schema trung tâm của toàn bộ hệ thống.** Mọi agent đọc/ghi metadata qua schema này. Là "ngôn ngữ chung" giữa connectors và agents.

**Các class chính**:
| Class | Vai trò |
|-------|---------|
| `CMSAuthor` | Tên tác giả đã chuẩn hóa, có validator strip whitespace |
| `CMSJournal` | Title, ISSN-L, publisher của tạp chí |
| `CanonicalMetadataSchema` | Schema đầy đủ: DOI, title, pub_year, pub_date, journal, authors, flags, **provenance** |

**Provenance là gì và tại sao quan trọng?**
Mỗi CMS object bắt buộc có 3 field:
- `source_api`: `"crossref"` hoặc `"openalex"` — dữ liệu đến từ đâu
- `source_url`: URL thực tế đã gọi — để audit lại sau này
- `fetched_at`: Thời điểm fetch — để biết dữ liệu cũ hay mới

Đây là cơ chế chống hallucination: mọi thông tin đều truy xuất được nguồn gốc.

**Validation**:
- DOI normalization: strip `doi:`, `https://doi.org/`, lowercase
- DOI format check: regex `10.\d{4,9}/.+`
- pub_date year phải khớp pub_year (cross-field validator)

#### `src/reviewagent/schemas/submission.py`
**Vai trò**: Schema cho request/response của API submission.

| Class | Vai trò |
|-------|---------|
| `SubmissionStatus` | Enum: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |
| `SubmissionCreateRequest` | Input: `doi` string, có validator chuẩn hóa DOI |
| `SubmissionCreateResponse` | Output: `submission_id` (UUID), `status`, `decision_id` |

#### `src/reviewagent/schemas/decision.py`
**Vai trò**: Schema cho kết quả quyết định — output của decision agent.

| Class | Vai trò |
|-------|---------|
| `DecisionLabel` | Enum: `APPROVE`, `REVIEW`, `REJECT` |
| `DecisionResult` | confidence_raw, confidence_calibrated, rationale, flags, sub_scores |

**Flags**: Danh sách các cờ cảnh báo dạng machine-readable. Ví dụ: `MISSING_ISSN`, `RETRACTED`, `UNKNOWN_AUTHORS`. Có validator dedup và trim whitespace.

**Sub-scores**: Dict các điểm thành phần (metadata_completeness, source_reliability, ...). Mỗi value phải trong [0, 1].

---

### 4.3. Layer Connectors (External APIs)

#### `src/reviewagent/connectors/base.py`
**Vai trò**: Base class cho mọi HTTP connector. Đóng gói toàn bộ logic HTTP chung.

**Kiến trúc**:
```
BaseConnector
  ├── base_url: str              # URL gốc của API
  ├── source_name: str           # Tên nguồn (dùng trong error message)
  ├── _client: httpx.AsyncClient # Client HTTP (lazy init)
  ├── _get(path, params)         # GET request → JSON dict
  ├── aclose()                   # Đóng HTTP client
  └── async context manager      # Dùng với `async with`
```

**Error handling trong `_get()`**:
| HTTP status | Hành vi |
|-------------|---------|
| 404 | Trả `{}` (dict rỗng) — coi là miss hợp lệ |
| 5xx | Raise `ConnectorError` — lỗi server |
| 4xx (khác 404) | Raise `ConnectorError` — lỗi client |
| Network error | Raise `ConnectorError` |
| JSON parse fail | Raise `ConnectorError` |

**Timeout mặc định**: connect 5s, read 15s, write 5s.

#### `src/reviewagent/connectors/crossref.py`
**Vai trò**: Connector chính thức cho Crossref REST API — nguồn metadata số 1.

**Luồng hoạt động**:
```
lookup(doi)
  → URL encode DOI
  → GET /works/{encoded_doi}
  → Nếu 404: return None
  → Nếu có dữ liệu: parse message
     → _extract_date(): thử published → published-print → published-online → issued
     → _extract_journal_title(): container-title → short-container-title
     → _extract_issn(): ISSN-L → ISSN[0]
     → _extract_authors(): ghép given + family → CMSAuthor
  → Build CanonicalMetadataSchema (source_api="crossref")
```

**Polite pool**: Crossref yêu cầu `User-Agent` chứa mailto. Mặc định dùng `reviewagent@ptit.edu.vn`.

**Các field bắt buộc để parse thành công**: title, pub_year, journal_title. Thiếu 1 trong 3 → return None.

#### `src/reviewagent/connectors/openalex.py`
**Vai trò**: Connector fallback cho OpenAlex API — dùng khi Crossref không có dữ liệu.

**Luồng hoạt động**:
```
lookup(doi)
  → GET /works/https://doi.org/{encoded_doi}
  → Nếu 404: return None
  → Nếu có dữ liệu: parse work
     → _extract_date(): publication_year + publication_date
     → _extract_journal(): primary_location.source.display_name → issn_l
                          → fallback: duyệt locations[] tìm source có display_name
     → _extract_authors(): authorships[].author.display_name → CMSAuthor
  → Build CanonicalMetadataSchema (source_api="openalex")
```

**Khác biệt với Crossref**:
- OpenAlex không expose `publisher` ở work level → field này luôn None
- OpenAlex dùng `authorships` thay vì `author`
- Date format: OpenAlex dùng ISO string thay vì date-parts array

---

### 4.4. Layer Agents (Business Logic)

#### `src/reviewagent/agents/state.py`
**Vai trò**: Định nghĩa `ReviewState` — object mang dữ liệu xuyên suốt pipeline.

```python
@dataclass
class ReviewState:
    submission_id: UUID          # ID của submission trong DB
    doi: str                     # DOI đã chuẩn hóa
    cms: CMS | None              # Metadata đã fetch và chuẩn hóa
    decision: DecisionResult | None  # Kết quả decision
    errors: list[str]            # Danh sách lỗi trong quá trình xử lý
    metadata_source: str | None  # "crossref" hoặc "openalex"
    prompt_version: str          # Version của prompt đã dùng
```

#### `src/reviewagent/agents/metadata_agent.py`
**Vai trò**: **Agent đầu tiên trong pipeline.** Nhận DOI, gọi connectors để lấy metadata, chuẩn hóa thành CMS.

**Luồng xử lý**:
```
fetch_metadata_for_doi(doi)
  1. Gọi CrossrefConnector.lookup(doi)
     → Thành công: return CMS ngay (source="crossref")
     → Thất bại: ghi lỗi, tiếp tục bước 2
  
  2. Gọi OpenAlexConnector.lookup(doi)
     → Thành công: return CMS (source="openalex")
     → Thất bại: ghi lỗi
  
  3. Cả hai đều thất bại:
     → return MetadataAgentResult(cms=None, needs_review=True, errors=[...])
```

**Pattern quan trọng**:
- `MetadataAgentResult` là frozen dataclass — immutable, an toàn khi pass qua các layer
- Agent tự quản lý vòng đời connector (tạo mới nếu không được inject, tự đóng sau khi dùng)
- `needs_review=True` khi cả hai nguồn đều fail → pipeline sẽ xử lý fail-safe

#### `src/reviewagent/agents/decision_agent.py`
**Vai trò**: **Agent thứ hai trong pipeline.** Nhận CMS, đưa ra quyết định APPROVE/REVIEW/REJECT.

**Hai đường xử lý**:

**Đường 1 — LLM (khi có API key)**:
```
CMS → _cms_to_input() → dict JSON
  → LLMGateway.generate_decision_v1(input_data)
  → LLM trả JSON → parse → DecisionResult
  → Nếu LLM lỗi: fallback xuống rule-based
```

**Đường 2 — Rule-based (khi không có API key)**:
```
CMS → _rule_based_decision()
  → Tính metadata_completeness:
      base 0.5 + 0.25 nếu có ISSN + 0.25 nếu có publisher
  → Tính source_reliability:
      0.8 nếu crossref, 0.6 nếu openalex
  → confidence_raw = 0.5 * metadata + 0.5 * source
  → Nếu retracted: confidence = 0.1, REJECT
  → confidence >= 0.75 → APPROVE
  → confidence >= 0.5  → REVIEW
  → confidence < 0.5   → REVIEW (vẫn REVIEW, không REJECT trong PoC)
```

**Sub-scores**: `metadata_completeness` và `source_reliability` — mỗi cái [0, 1].

#### `src/reviewagent/agents/graph.py`
**Vai trò**: **Orchestrator** — kết nối metadata agent và decision agent thành pipeline hoàn chỉnh.

```python
class ReviewPipeline:
    async def run(submission_id, doi) -> ReviewState:
        # Step 1: Metadata
        meta_result = await metadata_agent.run(doi)
        
        # Step 2: Nếu không có metadata → dừng
        if meta_result.cms is None:
            return state với errors
        
        # Step 3: Decision
        decision_result = await decision_agent.run(cms, errors)
        
        # Step 4: Trả state đầy đủ
        return ReviewState(cms=..., decision=...)
```

**Điểm quan trọng**: Graph này là **tuần tự** (sequential). Phase MVP sẽ nâng cấp lên LangGraph parallel.

---

### 4.5. Layer LLM (AI Gateway)

#### `src/reviewagent/llm/gateway.py`
**Vai trò**: Cổng giao tiếp với LLM. Đóng gói việc gọi model và parse response.

**Thiết kế**:
```python
class LLMGateway:
    completion: Callable | None  # Async function gọi LLM thật
    
    async def generate_decision(prompt, input_data) -> DecisionResult:
        if completion is None:
            return REVIEW result  # Fallback khi chưa cấu hình LLM
        response = await completion(model, system_prompt, user_prompt)
        return parse JSON → DecisionResult
```

**Pattern quan trọng**: `completion` là **dependency injection** — không hardcode Anthropic SDK. Để tích hợp LLM thật:
```python
async def my_completion(model, system, user):
    # Gọi Anthropic SDK ở đây
    return json_string

gateway = LLMGateway(completion=my_completion)
```

**`_review_result()`**: Fallback khi không có LLM — trả `REVIEW` với confidence 0.0, flag `LLM_NOT_CONFIGURED`.

#### `src/reviewagent/llm/prompts/decision_v1.py`
**Vai trò**: System prompt + user prompt builder cho decision agent.

**System prompt yêu cầu model**:
1. Chỉ dùng CMS evidence, không dùng memory
2. Thiếu metadata → `REVIEW`
3. Chỉ trả JSON theo schema cố định
4. Rationale ngắn, trích dẫn field cụ thể từ input

**User prompt**: `build_decision_user_prompt(input_data)` — nhúng CMS JSON vào prompt.

#### `src/reviewagent/llm/calibration.py`
**Vai trò**: Hiệu chỉnh confidence score.

**Hiện tại**: Identity function — `calibrate_confidence(x) = x`. Đây là placeholder cho Platt scaling sẽ triển khai khi có đủ dữ liệu huấn luyện.

---

### 4.6. Layer Database

#### `src/reviewagent/db/session.py`
**Vai trò**: Khởi tạo SQLAlchemy async engine và session maker.

**Cấu trúc**:
```python
engine = create_async_engine(url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_async_session() -> AsyncIterator[AsyncSession]:
    # Generator để FastAPI Depends() dùng
```

**`Base`**: Declarative base cho tất cả ORM models.

#### `src/reviewagent/db/models/submission.py`
**Vai trò**: Bảng `submissions` — lưu input người dùng.

| Column | Type | Mô tả |
|--------|------|-------|
| `id` | UUID PK | ID submission |
| `doi` | String(512) | DOI đã chuẩn hóa |
| `status` | Enum(PENDING/PROCESSING/COMPLETED/FAILED) | Trạng thái xử lý |
| `publication_id` | UUID FK → publications | Liên kết tới metadata |
| `created_at` | DateTime | Timestamp tạo |
| `updated_at` | DateTime | Timestamp cập nhật cuối |

**Relationships**: `publication` (many-to-one), `decision` (one-to-one).

#### `src/reviewagent/db/models/publication.py`
**Vai trò**: Bảng `publications` — cache metadata đã fetch, tránh gọi lại API cho cùng DOI.

| Column | Type | Mô tả |
|--------|------|-------|
| `id` | UUID PK | ID publication |
| `doi` | String(512) UNIQUE | DOI (unique constraint) |
| `title` | Text | Tiêu đề bài báo |
| `pub_year` | Integer | Năm xuất bản |
| `pub_date` | Date | Ngày xuất bản |
| `cms` | JSONB | Toàn bộ CMS object dạng JSON |
| `provenance` | JSONB | source_api + source_url |

**Unique constraint trên DOI**: Mỗi DOI chỉ cached 1 lần.

#### `src/reviewagent/db/models/decision.py`
**Vai trò**: Bảng `decisions` — lưu kết quả quyết định.

| Column | Type | Mô tả |
|--------|------|-------|
| `id` | UUID PK | ID decision |
| `submission_id` | UUID FK UNIQUE | 1-1 với submission |
| `decision` | Enum(APPROVE/REVIEW/REJECT) | Quyết định |
| `confidence_raw` | Float | Điểm thô |
| `confidence_calibrated` | Float | Điểm đã calibration |
| `rationale` | Text | Giải thích |
| `flags` | JSONB | Danh sách cờ |
| `evidence` | JSONB | Sub-scores và evidence |
| `model_version` | String | Model đã dùng |
| `prompt_version` | String | Prompt version |

#### `src/reviewagent/db/repositories/submission_repo.py`
**Vai trò**: Data access layer cho submissions.

| Hàm | Mô tả |
|------|-------|
| `create_submission(session, doi, status)` | Tạo submission mới |
| `get_submission_by_id(session, id)` | Lấy theo ID |
| `update_submission_status(session, id, status)` | Cập nhật trạng thái |
| `get_latest_submission_by_doi(session, doi)` | Tìm submission gần nhất cho DOI |

#### `src/reviewagent/db/repositories/decision_repo.py`
**Vai trò**: Data access layer cho decisions.

| Hàm | Mô tả |
|------|-------|
| `save_decision(session, ...)` | Lưu decision mới |
| `get_decision_by_id(session, id)` | Lấy theo ID |
| `get_decision_by_submission_id(session, submission_id)` | Lấy theo submission |

---

### 4.7. Layer API (FastAPI)

#### `src/reviewagent/api/deps.py`
**Vai trò**: Dependency injection — cung cấp DB session và pipeline cho routers.

```python
async def get_db() -> AsyncSession:  # Generator → FastAPI Depends
def get_pipeline() -> ReviewPipeline:  # Singleton pipeline
```

#### `src/reviewagent/api/main.py`
**Vai trò**: FastAPI app factory. Tạo app, đăng ký routers, cấu hình lifespan.

**Cấu trúc**:
```python
def create_app() -> FastAPI:
    app = FastAPI(title=..., lifespan=...)
    app.include_router(health.router)
    app.include_router(submissions.router)
    app.include_router(decisions.router)
    return app

app = create_app()  # Module-level để uvicorn import
```

**Lifespan**: Lưu settings vào `app.state.settings` khi startup.

**Swagger UI**: Chỉ bật ở `development` mode (qua `docs_url`).

#### `src/reviewagent/api/routers/health.py`
**Vai trò**: `GET /health` — kiểm tra app và database.

**Response**:
```json
{"status": "ok", "database": "ok"}
// hoặc
{"status": "ok", "database": "unavailable"}
```

#### `src/reviewagent/api/routers/submissions.py`
**Vai trò**: `POST /submissions` — endpoint chính của Phase 1.

**Luồng xử lý trong endpoint**:
```
1. Nhận DOI từ request body → validate bằng SubmissionCreateRequest
2. Tạo Submission record (status=PROCESSING)
3. Gọi pipeline.run(submission_id, doi)
   → Metadata agent → Decision agent
4. Nếu có CMS: tạo Publication record, link vào submission
5. Nếu có Decision: save decision → update status COMPLETED → return response
6. Nếu có errors: update status FAILED → return 422
7. Nếu exception: rollback → update status FAILED → return 500
```

**Transaction management**:
- Thành công: `await db.commit()` sau khi lưu decision
- Thất bại: `await db.rollback()` rồi update submission status FAILED riêng

#### `src/reviewagent/api/routers/decisions.py`
**Vai trò**: Endpoint truy xuất kết quả.

**2 endpoints**:
- `GET /decisions/{decision_id}` — lấy theo decision UUID
- `GET /decisions?submission_id=<uuid>` — lấy theo submission UUID

**Response**: `DecisionResponse` — decision_id, submission_id, decision label, confidence, rationale, flags, evidence.

---

### 4.8. Scripts

#### `scripts/migrate.py`
**Vai trò**: Tạo bảng database (thay cho Alembic migration trong PoC).

```bash
python scripts/migrate.py upgrade
# → Created tables: decisions, publications, submissions
```

#### `scripts/eval.py`
**Vai trò**: Script đánh giá chất lượng pipeline trên dataset. Dùng để đo baseline F1.

---

### 4.9. Tests

#### `tests/unit/test_schemas.py`
**Vai trò**: 6 unit tests cho schemas.

| Test | Kiểm tra gì |
|------|-------------|
| `test_submission_request_normalizes_doi` | DOI normalization: strip `https://doi.org/`, lowercase |
| `test_submission_request_rejects_invalid_doi` | Input sai format → ValidationError |
| `test_cms_requires_grounded_provenance_and_normalizes_doi` | CMS có provenance, DOI normalized |
| `test_cms_rejects_pub_date_year_mismatch` | pub_date năm 2023 mà pub_year 2024 → lỗi |
| `test_decision_result_keeps_structured_output_shape` | Flags dedup, sub_scores đúng |
| `test_submission_response_supports_basic_phase1_shape` | Response shape đúng |

---

## 5. Thứ tự code và dependency

Đây là thứ tự đã code trong thực tế. Mỗi bước phụ thuộc vào các bước trước.

### Giai đoạn 1: Foundation (files 1-3)

```
1. pyproject.toml
   → Không phụ thuộc file nào
   → Khai báo dependencies cho toàn project

2. .env.example
   → Không phụ thuộc file nào
   → Template biến môi trường

3. config.py
   → Phụ thuộc: .env.example (biến khai báo)
   → Module nền — mọi file sau đều import
```

### Giai đoạn 2: Schemas (files 4-6)

```
4. schemas/cms.py
   → Phụ thuộc: không (chỉ dùng Pydantic)
   → Schema trung tâm — connectors và agents đều dùng

5. schemas/submission.py
   → Phụ thuộc: không
   → Schema cho API input/output

6. schemas/decision.py
   → Phụ thuộc: không
   → Schema cho decision output
```

### Giai đoạn 3: Connectors (files 7-9)

```
7. connectors/base.py
   → Phụ thuộc: không (chỉ dùng httpx)
   → Base class cho các connector

8. connectors/crossref.py
   → Phụ thuộc: base.py, schemas/cms.py
   → Connector chính

9. connectors/openalex.py
   → Phụ thuộc: base.py, schemas/cms.py
   → Connector fallback
```

### Giai đoạn 4: Database (files 10-16)

```
10. db/session.py
    → Phụ thuộc: config.py
    → Engine và session maker

11. db/models/submission.py
    → Phụ thuộc: session.py, schemas/submission.py

12. db/models/publication.py
    → Phụ thuộc: session.py

13. db/models/decision.py
    → Phụ thuộc: session.py, schemas/decision.py

14. db/models/__init__.py
    → Phụ thuộc: 3 model files trên

15. db/repositories/submission_repo.py
    → Phụ thuộc: models/submission.py, schemas/submission.py

16. db/repositories/decision_repo.py
    → Phụ thuộc: models/decision.py, schemas/decision.py
```

### Giai đoạn 5: LLM (files 17-19)

```
17. llm/prompts/decision_v1.py
    → Phụ thuộc: không (chỉ là string constants)

18. llm/calibration.py
    → Phụ thuộc: không

19. llm/gateway.py
    → Phụ thuộc: config.py, calibration.py, prompts/decision_v1.py, schemas/decision.py
```

### Giai đoạn 6: Agents (files 20-23)

```
20. agents/state.py
    → Phụ thuộc: schemas/cms.py, schemas/decision.py

21. agents/metadata_agent.py
    → Phụ thuộc: connectors/crossref.py, connectors/openalex.py, schemas/cms.py

22. agents/decision_agent.py
    → Phụ thuộc: llm/gateway.py, schemas/cms.py, schemas/decision.py

23. agents/graph.py
    → Phụ thuộc: state.py, metadata_agent.py, decision_agent.py
```

### Giai đoạn 7: API (files 24-28)

```
24. api/deps.py
    → Phụ thuộc: config.py, db/session.py, agents/graph.py

25. api/routers/health.py
    → Phụ thuộc: deps.py

26. api/routers/submissions.py
    → Phụ thuộc: deps.py, agents/graph.py, db/repositories/*, db/models/publication.py

27. api/routers/decisions.py
    → Phụ thuộc: deps.py, db/repositories/decision_repo.py

28. api/main.py
    → Phụ thuộc: routers/health.py, routers/submissions.py, routers/decisions.py
```

### Giai đoạn 8: Infrastructure & Docs (files 29-31)

```
29. docker/docker-compose.yml
    → Không phụ thuộc code Python

30. scripts/migrate.py
    → Phụ thuộc: db/session.py, db/models/__init__.py

31. README.md
    → Viết sau cùng, tổng kết tất cả
```

---

## 6. Cách test từng phần

### Test 1: Schema validation (không cần network, không cần DB)

```bash
pytest tests/unit/test_schemas.py -v
```

### Test 2: Config loading

```bash
python -c "from reviewagent.config import get_settings; s = get_settings(); print(s.app.name, s.database.url)"
```

### Test 3: Connectors (cần network)

```bash
python -c "
import asyncio
from reviewagent.connectors.crossref import CrossrefConnector
async def t():
    async with CrossrefConnector() as c:
        r = await c.lookup('10.1109/5.771073')
        print(f'Title: {r.title}')
        print(f'Journal: {r.journal.title}')
        print(f'Year: {r.pub_year}')
        print(f'Authors: {[a.full_name for a in r.authors]}')
asyncio.run(t())
"
```

### Test 4: Metadata agent (cần network)

```bash
python -c "
import asyncio
from uuid import uuid4
from reviewagent.agents.metadata_agent import MetadataAgent
async def t():
    agent = MetadataAgent()
    r = await agent.run('10.1109/5.771073')
    print(f'Source: {r.source}')
    print(f'CMS: {r.cms is not None}')
    print(f'Errors: {r.errors}')
asyncio.run(t())
"
```

### Test 5: Decision agent (không cần network, không cần LLM)

```bash
python -c "
import asyncio
from reviewagent.agents.decision_agent import DecisionAgent
from reviewagent.schemas.cms import CMSAuthor, CMSJournal, CanonicalMetadataSchema
from datetime import datetime, timezone
async def t():
    cms = CanonicalMetadataSchema(
        doi='10.1000/test',
        title='Test Paper',
        pub_year=2024,
        journal=CMSJournal(title='Test Journal', issn_l='1234-5678', publisher='Test Pub'),
        authors=[CMSAuthor(full_name='John Smith')],
        source_api='crossref',
        source_url='https://api.crossref.org/works/10.1000/test',
        fetched_at=datetime.now(tz=timezone.utc),
    )
    agent = DecisionAgent()
    r = await agent.run(cms)
    print(f'Decision: {r.decision.decision}')
    print(f'Confidence: {r.decision.confidence_raw}')
    print(f'Source: {r.source}')
asyncio.run(t())
"
```

### Test 6: DB models + migration (cần PostgreSQL)

```bash
# Tạo bảng
python scripts/migrate.py upgrade

# Test CRUD
python -c "
import asyncio
from reviewagent.db.session import AsyncSessionLocal
from reviewagent.db.repositories.submission_repo import create_submission, get_submission_by_id

async def t():
    async with AsyncSessionLocal() as s:
        sub = await create_submission(s, '10.1000/test')
        print(f'Created: {sub.id}')
        found = await get_submission_by_id(s, sub.id)
        print(f'Found: {found.doi}')
asyncio.run(t())
"
```

### Test 7: API endpoints (cần PostgreSQL + server chạy)

```bash
# Terminal 1: Chạy server
uvicorn reviewagent.api.main:app --reload --port 8000

# Terminal 2: Gọi API
curl -X POST http://localhost:8000/submissions \
  -H "Content-Type: application/json" \
  -d '{"doi": "10.1109/5.771073"}'

curl http://localhost:8000/health
```

### Test 8: Full pipeline integration (cần network, cần PostgreSQL)

```bash
python -c "
import asyncio
from uuid import uuid4
from reviewagent.agents.graph import ReviewPipeline
from reviewagent.db.session import AsyncSessionLocal
from reviewagent.db.repositories.submission_repo import create_submission
from reviewagent.schemas.submission import SubmissionStatus

async def t():
    async with AsyncSessionLocal() as s:
        sub = await create_submission(s, '10.1109/5.771073', SubmissionStatus.PROCESSING)
        pipeline = ReviewPipeline()
        state = await pipeline.run(sub.id, '10.1109/5.771073')
        print(f'CMS fetched: {state.cms is not None}')
        print(f'Decision: {state.decision.decision if state.decision else None}')
        print(f'Confidence: {state.decision.confidence_raw if state.decision else None}')
        print(f'Errors: {state.errors}')
asyncio.run(t())
"
```

---

## 7. Checklist hoàn thành Phase 1

### Infrastructure
- [x] `pyproject.toml` — dependencies khai báo đủ
- [x] `.env.example` — biến môi trường đầy đủ

### Config
- [x] `config.py` — load settings từ env

### Schemas
- [x] `schemas/cms.py` — CMS có provenance, DOI validation
- [x] `schemas/submission.py` — Request/Response models
- [x] `schemas/decision.py` — DecisionResult structured output

### Connectors
- [x] `connectors/base.py` — Base HTTP client với error handling
- [x] `connectors/crossref.py` — Crossref lookup + CMS mapping
- [x] `connectors/openalex.py` — OpenAlex fallback + CMS mapping

### Database
- [x] `db/session.py` — Async SQLAlchemy engine
- [x] `db/models/submission.py` — Submission ORM
- [x] `db/models/publication.py` — Publication ORM (CMS cache)
- [x] `db/models/decision.py` — Decision ORM
- [x] `db/repositories/submission_repo.py` — CRUD submissions
- [x] `db/repositories/decision_repo.py` — CRUD decisions

### LLM
- [x] `llm/prompts/decision_v1.py` — System + user prompt
- [x] `llm/calibration.py` — Calibration stub
- [x] `llm/gateway.py` — LLM wrapper với fallback

### Agents
- [x] `agents/state.py` — ReviewState dataclass
- [x] `agents/metadata_agent.py` — Crossref → OpenAlex fallback
- [x] `agents/decision_agent.py` — LLM + rule-based decision
- [x] `agents/graph.py` — Sequential pipeline orchestrator

### API
- [x] `api/deps.py` — DB session + pipeline injection
- [x] `api/routers/health.py` — GET /health
- [x] `api/routers/submissions.py` — POST /submissions
- [x] `api/routers/decisions.py` — GET /decisions
- [x] `api/main.py` — FastAPI app factory

### Scripts & Infra
- [x] `scripts/migrate.py` — Tạo bảng DB
- [x] `scripts/eval.py` — Evaluation script
- [x] `docker/docker-compose.yml` — PostgreSQL dev
- [x] `README.md` — Hướng dẫn chạy

### Tests
- [x] `tests/unit/test_schemas.py` — 6 schema tests (pass)
- [ ] `tests/unit/test_crossref_connector.py` — (chưa viết)
- [ ] `tests/unit/test_openalex_connector.py` — (chưa viết)
- [ ] `tests/integration/test_submissions_api.py` — (chưa viết)
- [ ] `tests/integration/test_review_pipeline.py` — (chưa viết)

---

## Phụ lục: Câu hỏi thường gặp

**Q: Tại sao có 2 connector (Crossref + OpenAlex)?**
A: Crossref là nguồn chính thống nhất cho metadata học thuật, nhưng không cover 100% DOI. OpenAlex là nguồn mở, coverage rộng hơn, dùng làm fallback. Nguyên tắc: Crossref trước (chất lượng cao hơn), OpenAlex sau (coverage rộng hơn).

**Q: Tại sao CMS có `source_api` và `source_url` bắt buộc?**
A: Đây là cơ chế "grounding" — mọi thông tin phải truy xuất được nguồn gốc. Khi audit, người review có thể click URL để xem dữ liệu gốc. Đây cũng là cơ chế chống hallucination: LLM không thể tự bịa metadata vì mọi field phải có provenance.

**Q: Nếu không có API key LLM thì sao?**
A: Hệ thống tự động chuyển sang rule-based decision. Không có LLM, hệ thống vẫn chạy được nhưng chất lượng decision sẽ thấp hơn (chỉ dựa trên metadata completeness + source reliability).

**Q: Khi nào cần REVIEW thay vì APPROVE?**
A: Rule-based: confidence < 0.75. LLM-based: model tự quyết định dựa trên prompt (thiếu evidence → REVIEW). Nguyên tắc: "when in doubt, REVIEW" — thà để người kiểm tra còn hơn approve sai.

**Q: Tại sao không dùng Alembic migration?**
A: Phase 1 PoC dùng `create_all` cho đơn giản. Alembic sẽ được thêm ở Phase MVP khi schema ổn định hơn.
