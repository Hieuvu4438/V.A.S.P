# Phase 1 PoC Backend + AI — Bảng file cần code

## Phạm vi

Tài liệu này liệt kê các file cần tập trung code trong **Phase 1 / PoC** khi hệ thống chỉ làm **AI + backend**, **chưa làm frontend**.

Mục tiêu của phase này là tạo được luồng tối thiểu chạy end-to-end:

**POST submission → lấy metadata từ Crossref/OpenAlex → chuẩn hoá CMS → decision → lưu DB → trả kết quả → eval/test**

Căn cứ chính:
- `DOCUMENT/implementation_plan.md`
- Phase PoC tại `DOCUMENT/implementation_plan.md:401`

---

## Bảng file → cần code gì

| STT | File | Mục đích | Nội dung cần code trong phase này |
|---|---|---|---|
| 1 | `pyproject.toml` | Cấu hình project Python | Khai báo dependencies tối thiểu cho FastAPI, Pydantic v2, SQLAlchemy async, httpx, pytest, mypy, LangGraph/LiteLLM nếu dùng trong PoC; cấu hình build tool và test/lint cơ bản. |
| 2 | `.env.example` | Mẫu biến môi trường | Thêm các biến như `APP_ENV`, `APP_NAME`, `API_HOST`, `API_PORT`, `DATABASE_URL`, `CROSSREF_BASE_URL`, `OPENALEX_BASE_URL`, `ANTHROPIC_API_KEY` hoặc khóa LLM tương ứng, `LOG_LEVEL`. |
| 3 | `src/reviewagent/config.py` | Quản lý cấu hình | Tạo `Settings` bằng `pydantic-settings`; parse env; nhóm cấu hình app, DB, external APIs, LLM; cung cấp singleton/hàm load settings cho toàn app. |
| 4 | `src/reviewagent/api/main.py` | App factory FastAPI | Khởi tạo FastAPI app; đăng ký lifespan nếu cần; include các router PoC; cấu hình metadata API; bật endpoint docs; wiring health/submission/decision routes. |
| 5 | `src/reviewagent/api/deps.py` | Dependency injection | Cung cấp dependency lấy settings, DB session, connector service, review pipeline service; dùng cho router PoC. |
| 6 | `src/reviewagent/api/routers/submissions.py` | Endpoint tạo submission | Tạo `POST /submissions`; nhận DOI và metadata user khai; validate input; gọi pipeline review; trả `submission_id`, trạng thái, decision và evidence cơ bản. |
| 7 | `src/reviewagent/api/routers/decisions.py` | Endpoint xem quyết định | Tạo `GET /decisions/{id}` hoặc endpoint tương đương để truy xuất kết quả đã lưu; trả decision, confidence, rationale, CMS tóm tắt. |
| 8 | `src/reviewagent/api/routers/health.py` | Healthcheck | Tạo `/health`; trả trạng thái app; có thể kiểm DB/connectors ở mức nhẹ. |
| 9 | `src/reviewagent/schemas/cms.py` | Canonical Metadata Schema | Hoàn thiện schema CMS cho DOI, title, pub year, journal, authors, flags, provenance; validate DOI format; bắt buộc `source_api`, `source_url`, `fetched_at`; chuẩn hoá field names cho toàn pipeline. |
| 10 | `src/reviewagent/schemas/submission.py` | Schema input/output submission | Tạo model request/response cho submit bài; định nghĩa input tối thiểu ưu tiên case có DOI; response gồm `submission_id`, `status`, `decision_id` nếu có. |
| 11 | `src/reviewagent/schemas/decision.py` | Schema quyết định | Tạo model `APPROVE | REVIEW | REJECT`; chứa `confidence_raw`, `confidence_calibrated`, `sub_scores`, `rationale`, `flags`, `evidence_panel`; đảm bảo structured output rõ ràng. |
| 12 | `src/reviewagent/connectors/base.py` | Base HTTP connector | Tạo lớp base dùng `httpx.AsyncClient`; chuẩn hoá timeout, headers, error handling, request helper; có kiểu kết quả thống nhất để Crossref/OpenAlex dùng lại. |
| 13 | `src/reviewagent/connectors/crossref.py` | Connector Crossref | Implement lookup theo DOI; gọi API Crossref; parse response; map về dữ liệu tương thích CMS; gắn `source_api='crossref'`; xử lý 404 là miss hợp lệ. |
| 14 | `src/reviewagent/connectors/openalex.py` | Connector OpenAlex | Implement fallback lookup theo DOI; parse response OpenAlex; map về CMS-compatible fields; gắn `source_api='openalex'`; dùng khi Crossref không trả kết quả hoặc thiếu dữ liệu. |
| 15 | `src/reviewagent/agents/state.py` | Trạng thái pipeline | Định nghĩa `ReviewState` hoặc model state chứa input submission, CMS, decision, errors, timing, model/prompt version; đủ cho graph tuần tự PoC. |
| 16 | `src/reviewagent/agents/metadata_agent.py` | Agent lấy metadata | Nhận DOI; gọi Crossref trước, OpenAlex fallback; hợp nhất/chuẩn hoá metadata; build CMS; fail-safe nếu không đủ nguồn xác thực. |
| 17 | `src/reviewagent/agents/decision_agent.py` | Agent ra quyết định | Nhận CMS và evidence tối thiểu; tính sub-scores hoặc gọi LLM để ra decision có cấu trúc; bảo đảm nguyên tắc grounded, không hallucinate metadata; mặc định `REVIEW` khi thiếu evidence. |
| 18 | `src/reviewagent/agents/graph.py` | Orchestration PoC | Dựng graph/pipeline tuần tự: submission → metadata agent → decision agent → persist; chưa cần fan-out song song; có interface gọi từ API. |
| 19 | `src/reviewagent/llm/gateway.py` | Cổng gọi LLM | Tạo wrapper gọi model; inject system prompt; ép structured output; gom phần chọn model, retries tối thiểu, parse response; dùng cho decision agent. |
| 20 | `src/reviewagent/llm/prompts/decision_v1.py` | Prompt quyết định v1 | Viết prompt yêu cầu model chỉ đọc evidence từ CMS; trả decision có rationale ngắn; buộc `REVIEW` nếu thiếu chứng cứ; cấm tự suy diễn DOI/năm/chỉ mục ngoài dữ liệu đầu vào. |
| 21 | `src/reviewagent/llm/calibration.py` | Calibration điểm tin cậy | Nếu làm ngay trong PoC thì thêm hàm sigmoid/Platt scaling đơn giản để chuyển confidence thô sang calibrated; nếu chưa đủ dữ liệu có thể để stub rõ ràng. |
| 22 | `src/reviewagent/db/session.py` | Kết nối database | Tạo async engine, async session maker; cấu hình PostgreSQL; cung cấp dependency session cho API/repository. |
| 23 | `src/reviewagent/db/models/submission.py` | Model submission | Bảng lưu input người dùng gửi, DOI, trạng thái, timestamps; liên kết tới publication và decision. |
| 24 | `src/reviewagent/db/models/publication.py` | Model publication/CMS cache | Bảng lưu metadata chuẩn hoá theo DOI; cache/reuse metadata đã fetch; lưu provenance JSON hoặc các trường canonical chính. |
| 25 | `src/reviewagent/db/models/decision.py` | Model quyết định | Bảng lưu decision, confidence, rationale, flags, evidence JSON, prompt/model version; liên kết tới submission. |
| 26 | `src/reviewagent/db/repositories/submission_repo.py` | Repository submission | Tạo hàm create/get/update submission; tách truy vấn DB khỏi router/agent. |
| 27 | `src/reviewagent/db/repositories/decision_repo.py` | Repository decision | Tạo hàm save/get decision; đọc kết quả theo `decision_id` hoặc `submission_id`. |
| 28 | `scripts/eval.py` | Đánh giá chất lượng PoC | Chạy pipeline trên dataset seed; tính precision/recall/F1 cơ bản; xuất kết quả tổng quan; dùng cho baseline PoC. |
| 29 | `docker/docker-compose.yml` | Môi trường dev | Cấu hình PostgreSQL và service phụ trợ tối thiểu phục vụ dev/test; nếu chưa cần Redis thì có thể để placeholder hoặc chỉ dùng Postgres cho phase đầu. |
| 30 | `README.md` | Hướng dẫn chạy PoC | Viết hướng dẫn cài đặt, cấu hình env, chạy app, chạy DB, chạy test/eval, ví dụ request `POST /submissions`. |
| 31 | `tests/unit/test_schemas.py` | Unit test schema | Test validate DOI, pub year, required provenance fields, enum decision, serialization/deserialization. |
| 32 | `tests/unit/test_crossref_connector.py` | Unit test Crossref | Test parse response, DOI miss, mapping dữ liệu sang CMS fields. |
| 33 | `tests/unit/test_openalex_connector.py` | Unit test OpenAlex | Test fallback parse/mapping sang CMS; bảo đảm output nhất quán với schema nội bộ. |
| 34 | `tests/integration/test_submissions_api.py` | Integration test API | Test `POST /submissions` và luồng trả response hợp lệ; kiểm DB write; kiểm response có CMS/decision tối thiểu. |
| 35 | `tests/integration/test_review_pipeline.py` | Integration test pipeline | Test end-to-end từ DOI input đến metadata + decision; kiểm fail-safe khi connector không trả dữ liệu. |

---

## File có trong repo nhưng chưa cần ưu tiên ở Phase 1

### Để sau ở MVP/Production
- `src/reviewagent/agents/router_agent.py`
- `src/reviewagent/agents/journal_agent.py`
- `src/reviewagent/agents/author_agent.py`
- `src/reviewagent/agents/integrity_agent.py`
- `src/reviewagent/agents/appeal_agent.py`
- `src/reviewagent/connectors/doaj.py`
- `src/reviewagent/connectors/orcid.py`
- `src/reviewagent/connectors/retraction_watch.py`
- `src/reviewagent/connectors/ror.py`
- `src/reviewagent/snapshots/mjl.py`
- `src/reviewagent/snapshots/scimago.py`
- `src/reviewagent/snapshots/beall.py`
- `src/reviewagent/snapshots/updater.py`
- `src/reviewagent/author_nd/vietnamese.py`
- `src/reviewagent/author_nd/embeddings.py`
- `src/reviewagent/author_nd/disambiguation.py`
- `src/reviewagent/integrity/tortured_phrase.py`
- `src/reviewagent/integrity/scigen_detector.py`
- `src/reviewagent/integrity/chatgpt_fingerprint.py`
- `src/reviewagent/tasks/celery_app.py`
- `src/reviewagent/tasks/review_task.py`
- `src/reviewagent/tasks/snapshot_task.py`
- `src/reviewagent/cache/redis_client.py`
- `src/reviewagent/audit/worm_logger.py`
- `src/reviewagent/db/models/audit_log.py`
- `src/reviewagent/db/models/journal.py`
- `src/reviewagent/db/repositories/journal_repo.py`
- `src/reviewagent/observability/tracing.py`
- `src/reviewagent/observability/metrics.py`
- `src/reviewagent/api/routers/reviews.py`
- `src/reviewagent/api/routers/appeals.py`
- `src/reviewagent/api/routers/reports.py`
- `src/reviewagent/api/middleware.py`

---

## Thứ tự nên code

1. `pyproject.toml`, `.env.example`, `config.py`
2. `schemas/cms.py`, `schemas/submission.py`, `schemas/decision.py`
3. `connectors/base.py`, `crossref.py`, `openalex.py`
4. `db/session.py`, `db/models/*.py`, repositories
5. `llm/gateway.py`, `llm/prompts/decision_v1.py`, `llm/calibration.py`
6. `agents/state.py`, `metadata_agent.py`, `decision_agent.py`, `graph.py`
7. `api/main.py`, `api/deps.py`, `routers/*.py`
8. `scripts/eval.py`, tests, README, docker compose

---

## Mức hoàn thành tối thiểu của phase này

Phase 1 được xem là đủ khi:
- Có thể gọi `POST /submissions` với một DOI hợp lệ.
- Hệ thống lấy được metadata từ Crossref hoặc OpenAlex.
- Metadata được chuẩn hoá vào CMS có provenance.
- Hệ thống trả decision dạng structured output.
- Submission và decision được lưu DB.
- Có test + eval cơ bản để chứng minh pipeline chạy được.
