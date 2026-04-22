# Phase 1 PoC Backend + AI — Chia nhỏ từng phần để code + prompt mẫu cho AI

## Mục tiêu phase này

Chỉ triển khai **backend + AI PoC**, chưa làm frontend.
Luồng tối thiểu cần chạy được:

**POST submission → validate input → fetch Crossref/OpenAlex → normalize CMS → decision → save DB → return API response → test/eval**

Tài liệu này chia phase thành các phần rất nhỏ để có thể giao từng phần cho AI code theo thứ tự.

---

# Nguyên tắc dùng prompt

- Mỗi prompt chỉ nên yêu cầu AI làm **một phần nhỏ**.
- Sau mỗi bước nên yêu cầu AI:
  - chỉ sửa đúng file liên quan
  - không làm rộng hơn scope
  - không tự thêm frontend
  - không code tính năng MVP/Production
- Nên yêu cầu AI **đọc file trước khi sửa**.
- Sau mỗi 2–3 bước nên yêu cầu AI chạy test hoặc kiểm tra import/type đơn giản.

Mẫu hậu tố nên thêm vào hầu hết prompt:

```text
Chỉ làm đúng phạm vi của bước này. Không thêm frontend. Không làm các phần của MVP/Production. Ưu tiên code tối giản nhưng chạy được. Sau khi sửa xong, tóm tắt ngắn file nào đã đổi và còn thiếu gì.
```

---

# Thứ tự triển khai khuyến nghị

1. Foundation project
2. Config và env
3. Schema input/output
4. CMS schema
5. Connector base
6. Crossref connector
7. OpenAlex connector
8. DB session + models
9. Repository nhỏ
10. Metadata agent
11. Decision schema + prompt + gateway
12. Decision agent
13. Graph orchestration
14. API router
15. Health/decision endpoints
16. Tests
17. Eval script
18. README / docker compose tinh gọn

---

# PHẦN 1 — Foundation project

## Bước 1.1 — Chuẩn hóa `pyproject.toml`

### Mục tiêu
Tạo nền dependency tối thiểu để chạy PoC.

### File
- `pyproject.toml`

### Cần code
- khai báo package/backend dependencies tối thiểu
- FastAPI
- Pydantic v2
- SQLAlchemy async
- httpx
- pytest
- mypy
- uvicorn
- nếu đã xác định dùng LangGraph/LiteLLM thì thêm bản tối thiểu

### Prompt cho AI
```text
Hãy đọc file `pyproject.toml` và cập nhật nó cho phase 1 PoC của project ReviewAgent PTIT.

Mục tiêu của phase này chỉ là backend + AI PoC, chưa làm frontend, chưa làm Celery, chưa làm observability nâng cao.

Hãy cấu hình `pyproject.toml` ở mức tối thiểu để chạy được:
- FastAPI
- Pydantic v2
- pydantic-settings
- SQLAlchemy async
- asyncpg
- httpx
- uvicorn
- pytest
- pytest-asyncio
- mypy

Nếu hợp lý, thêm LangGraph và LiteLLM ở mức tối thiểu cho PoC. Không thêm các dependency của frontend hoặc production hạ tầng.

Giữ file gọn, rõ, chỉ thêm những gì thật sự cần cho phase này. Sau khi sửa, tóm tắt các dependency chính đã thêm.
```

---

## Bước 1.2 — Tạo `.env.example`

### File
- `.env.example`

### Cần code
- biến môi trường tối thiểu cho app, DB, external APIs, LLM

### Prompt cho AI
```text
Hãy tạo hoặc hoàn thiện file `.env.example` cho phase 1 PoC backend + AI.

Chỉ thêm các biến môi trường thật sự cần cho PoC:
- app env/name/host/port
- database url
- log level
- Crossref/OpenAlex base URL nếu cần
- LLM API key và model name nếu phase này dùng LLM

Không thêm biến cho frontend, SSO, ORCID, Celery, Redis production, Grafana, Kubernetes.

Trả về file `.env.example` gọn, có comment ngắn nếu thật sự cần.
```

---

# PHẦN 2 — Config

## Bước 2.1 — Viết `config.py`

### File
- `src/reviewagent/config.py`

### Cần code
- `Settings` với pydantic-settings
- load env
- nhóm config app/db/apis/llm
- helper lấy settings

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/config.py` và triển khai cấu hình cho phase 1 PoC backend + AI.

Yêu cầu:
- dùng `pydantic-settings`
- có class `Settings`
- gom các cấu hình tối thiểu cho app, database, Crossref, OpenAlex, LLM
- có giá trị mặc định hợp lý cho local dev nếu phù hợp
- code đơn giản, dễ import từ các module khác

Không thêm cấu hình cho frontend, SSO, Celery, Redis, observability nâng cao, ORCID, journal snapshots.
```

---

# PHẦN 3 — Schema request/response

## Bước 3.1 — Viết schema submission

### File
- `src/reviewagent/schemas/submission.py`

### Cần code
- request model cho submit DOI
- response model cơ bản
- trạng thái submission

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/schemas/submission.py` và triển khai các Pydantic model cho phase 1 PoC.

Scope của phase này:
- ưu tiên submission có DOI
- chưa cần hỗ trợ đầy đủ luồng không DOI
- chưa cần appeal/reviewer workflow

Cần có:
- request model cho tạo submission
- response model cho tạo submission
- status model hoặc enum cơ bản nếu cần
- validation DOI hợp lệ ở mức phù hợp

Giữ schema ngắn gọn, thực dụng, đúng với PoC.
```

---

## Bước 3.2 — Viết schema decision

### File
- `src/reviewagent/schemas/decision.py`

### Cần code
- enum decision
- sub-scores
- evidence/rationale cơ bản
- confidence raw/calibrated

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/schemas/decision.py` và triển khai schema quyết định cho phase 1 PoC.

Cần có tối thiểu:
- enum `APPROVE`, `REVIEW`, `REJECT`
- model decision result
- `confidence_raw`
- `confidence_calibrated`
- `rationale`
- `flags`
- nếu hợp lý thì có `sub_scores`

Thiết kế theo hướng structured output để sau này dùng được cho LLM decision agent. Không thêm các field chỉ dùng cho phase MVP/Production nếu chưa cần.
```

---

# PHẦN 4 — CMS schema

## Bước 4.1 — Triển khai CMS tối thiểu

### File
- `src/reviewagent/schemas/cms.py`

### Cần code
- DOI
- title
- pub_year
- journal tối thiểu
- authors tối thiểu
- provenance fields bắt buộc

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/schemas/cms.py` và triển khai Canonical Metadata Schema tối thiểu cho phase 1 PoC.

Yêu cầu quan trọng:
- metadata phải grounded từ nguồn chính thống
- schema phải có provenance tối thiểu: `source_api`, `source_url`, `fetched_at`
- validate DOI hợp lệ
- đủ để map dữ liệu từ Crossref/OpenAlex trong PoC

Trong phase này chỉ cần các trường thật sự cần để:
- xác thực DOI
- lưu title
- year/date cơ bản
- journal cơ bản
- authors cơ bản
- flags cơ bản

Không thêm quá nhiều field nâng cao nếu chưa dùng đến trong pipeline PoC.
```

---

# PHẦN 5 — Connector base

## Bước 5.1 — Base connector

### File
- `src/reviewagent/connectors/base.py`

### Cần code
- `httpx.AsyncClient`
- timeout
- request helper
- parse error cơ bản

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/connectors/base.py` và triển khai base connector cho các external API của phase 1 PoC.

Yêu cầu:
- dùng `httpx.AsyncClient`
- có cấu hình timeout
- có helper GET request tái sử dụng được
- chuẩn hóa lỗi ở mức đủ dùng
- code đơn giản để Crossref và OpenAlex kế thừa hoặc dùng lại

Không thiết kế abstraction quá mức. Chỉ cần mức tối thiểu, rõ ràng, phục vụ PoC.
```

---

# PHẦN 6 — Crossref connector

## Bước 6.1 — Lookup theo DOI

### File
- `src/reviewagent/connectors/crossref.py`

### Cần code
- fetch theo DOI
- parse response Crossref
- map sang dữ liệu nội bộ hoặc CMS

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/connectors/crossref.py` và triển khai connector Crossref cho phase 1 PoC.

Yêu cầu:
- lookup theo DOI
- gọi Crossref REST API
- parse các field cần thiết cho CMS: DOI, title, publication year/date, journal title, ISSN nếu có, authors nếu có
- gắn provenance từ Crossref
- nếu 404 thì coi là miss hợp lệ, không ném lỗi hệ thống

Giữ implementation thực dụng. Không làm journal quality checks, retraction logic nâng cao, hay các phần của MVP.
```

---

# PHẦN 7 — OpenAlex connector

## Bước 7.1 — Fallback theo DOI

### File
- `src/reviewagent/connectors/openalex.py`

### Cần code
- fetch theo DOI
- parse response
- fallback khi Crossref miss

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/connectors/openalex.py` và triển khai connector OpenAlex cho phase 1 PoC.

Yêu cầu:
- lookup theo DOI
- parse các field cần cho CMS tương tự Crossref connector
- dùng như fallback khi Crossref không có dữ liệu hoặc thiếu dữ liệu chính
- trả dữ liệu với provenance rõ ràng

Không làm search theo title, fuzzy match, citation graph, author disambiguation hay các tính năng MVP khác.
```

---

# PHẦN 8 — Database

## Bước 8.1 — Session database

### File
- `src/reviewagent/db/session.py`

### Cần code
- async engine
- session maker
- helper tạo session

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/session.py` và triển khai database session cho phase 1 PoC.

Yêu cầu:
- dùng SQLAlchemy async
- cấu hình engine từ settings
- có async session maker
- có helper/dependency để router và repository dùng được

Chỉ cần PostgreSQL cho PoC. Không thêm migration framework hoặc transaction abstraction phức tạp nếu chưa cần.
```

---

## Bước 8.2 — Model submission

### File
- `src/reviewagent/db/models/submission.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/models/submission.py` và triển khai model `Submission` cho phase 1 PoC.

Model cần đủ để lưu:
- submission id
- DOI user gửi
- trạng thái hiện tại
- created_at / updated_at
- liên kết publication và/hoặc decision nếu hợp lý

Thiết kế tối giản, phục vụ luồng PoC. Không thêm reviewer workflow, appeal, audit nâng cao.
```

---

## Bước 8.3 — Model publication

### File
- `src/reviewagent/db/models/publication.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/models/publication.py` và triển khai model `Publication` cho phase 1 PoC.

Model này dùng để lưu metadata chuẩn hóa theo DOI.

Cần tối thiểu:
- DOI chuẩn hóa
- title
- publication year/date cơ bản
- dữ liệu CMS hoặc các field canonical chính
- provenance tối thiểu nếu lưu được

Giữ model đơn giản, chưa cần tách quá nhiều bảng con.
```

---

## Bước 8.4 — Model decision

### File
- `src/reviewagent/db/models/decision.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/models/decision.py` và triển khai model `Decision` cho phase 1 PoC.

Model cần lưu tối thiểu:
- decision enum
- confidence raw/calibrated
- rationale
- flags
- evidence JSON nếu phù hợp
- model/prompt version nếu có
- liên kết với submission

Không thêm appeal history hay reviewer action ở bước này.
```

---

# PHẦN 9 — Repository nhỏ

## Bước 9.1 — Submission repository

### File
- `src/reviewagent/db/repositories/submission_repo.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/repositories/submission_repo.py` và triển khai repository tối thiểu cho `Submission`.

Cần có các hàm cơ bản:
- create submission
- get by id
- update status
- nếu hợp lý thì get by DOI gần nhất

Giữ repository nhỏ, trực tiếp, không tạo abstraction lớn.
```

---

## Bước 9.2 — Decision repository

### File
- `src/reviewagent/db/repositories/decision_repo.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/db/repositories/decision_repo.py` và triển khai repository tối thiểu cho `Decision`.

Cần có:
- save decision
- get decision by id
- get decision by submission id

Thiết kế nhỏ gọn, đúng với PoC.
```

---

# PHẦN 10 — Metadata agent

## Bước 10.1 — Agent lấy metadata từ connectors

### File
- `src/reviewagent/agents/metadata_agent.py`

### Cần code
- gọi Crossref trước
- fallback OpenAlex
- normalize CMS
- fail-safe nếu không đủ dữ liệu

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/agents/metadata_agent.py` và triển khai metadata agent cho phase 1 PoC.

Luồng cần có:
1. nhận DOI từ submission
2. gọi Crossref trước
3. nếu miss thì gọi OpenAlex fallback
4. chuẩn hóa dữ liệu thành CMS
5. nếu không lấy được metadata đủ tin cậy thì trả trạng thái fail-safe để pipeline đưa về REVIEW hoặc lỗi phù hợp

Không thêm logic journal quality, ORCID, author disambiguation, integrity detection.
```

---

# PHẦN 11 — LLM gateway + prompt + decision schema usage

## Bước 11.1 — Prompt decision v1

### File
- `src/reviewagent/llm/prompts/decision_v1.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/llm/prompts/decision_v1.py` và viết prompt v1 cho decision agent trong phase 1 PoC.

Prompt phải buộc model:
- chỉ dùng evidence từ CMS và dữ liệu đã được fetch
- không tự suy diễn metadata ngoài input
- nếu thiếu evidence thì chọn REVIEW
- trả reasoning ngắn, rõ, phục vụ backend PoC

Giữ prompt ngắn, rõ, dễ maintain.
```

---

## Bước 11.2 — LLM gateway

### File
- `src/reviewagent/llm/gateway.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/llm/gateway.py` và triển khai gateway tối thiểu cho việc gọi LLM ở phase 1 PoC.

Yêu cầu:
- đọc cấu hình model từ settings
- nhận prompt + input data
- trả structured result phù hợp với decision schema
- code đơn giản, đủ để decision agent dùng

Nếu repo đang dùng LiteLLM thì triển khai wrapper mỏng. Nếu chưa đủ context để tích hợp provider thật, hãy thiết kế interface gọn và rõ.
```

---

## Bước 11.3 — Calibration tối thiểu

### File
- `src/reviewagent/llm/calibration.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/llm/calibration.py` và triển khai phần calibration tối thiểu cho phase 1 PoC.

Nếu chưa có dữ liệu fit thật, hãy:
- tạo hàm giao diện rõ ràng cho calibration
- có thể dùng sigmoid/identity tạm thời nhưng phải rõ ràng, an toàn
- không giả vờ có Platt scaling thật nếu chưa có dataset fit

Giữ thiết kế sao cho sau này dễ thay bằng calibration thật.
```

---

# PHẦN 12 — Decision agent

## Bước 12.1 — Ra decision từ CMS

### File
- `src/reviewagent/agents/decision_agent.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/agents/decision_agent.py` và triển khai decision agent cho phase 1 PoC.

Input:
- CMS đã chuẩn hóa
- evidence/provenance tối thiểu

Output:
- decision schema structured
- `APPROVE`, `REVIEW`, hoặc `REJECT`
- confidence raw/calibrated
- rationale ngắn
- flags nếu có

Yêu cầu hành vi:
- nếu metadata thiếu hoặc nguồn không đáng tin cậy thì ưu tiên REVIEW
- không hallucinate thông tin ngoài CMS
- implementation tối giản, phù hợp PoC

Nếu cần, có thể kết hợp rule-based score đơn giản với LLM reasoning, nhưng đừng làm quá phức tạp.
```

---

# PHẦN 13 — Graph orchestration

## Bước 13.1 — Graph tuần tự PoC

### File
- `src/reviewagent/agents/state.py`
- `src/reviewagent/agents/graph.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/agents/state.py` và `src/reviewagent/agents/graph.py`, rồi triển khai graph/pipeline tuần tự cho phase 1 PoC.

Luồng tối thiểu:
- nhận input submission
- gọi metadata agent
- gọi decision agent
- trả về kết quả cuối cùng để API/router lưu DB và response

Chưa cần parallel LangGraph, chưa cần router agent, journal agent, author agent, integrity agent.

Giữ state và graph đơn giản, rõ, có thể gọi được từ API layer.
```

---

# PHẦN 14 — API endpoints

## Bước 14.1 — Endpoint tạo submission

### File
- `src/reviewagent/api/routers/submissions.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/api/routers/submissions.py` và triển khai endpoint tạo submission cho phase 1 PoC.

Yêu cầu:
- nhận request có DOI
- validate input bằng schema
- tạo submission trong DB
- gọi pipeline review
- lưu publication/decision nếu có
- trả response gọn, rõ, có decision hoặc trạng thái tương ứng

Không thêm reviewer queue, appeal, webhook, auth phức tạp ở bước này.
```

---

## Bước 14.2 — Endpoint xem decision

### File
- `src/reviewagent/api/routers/decisions.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/api/routers/decisions.py` và triển khai endpoint xem quyết định cho phase 1 PoC.

Cần có endpoint đọc decision theo id hoặc theo submission id, trả:
- decision
- confidence
- rationale
- flags
- metadata tóm tắt nếu phù hợp

Giữ endpoint đơn giản, chưa cần auth workflow hoàn chỉnh.
```

---

## Bước 14.3 — Health endpoint

### File
- `src/reviewagent/api/routers/health.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/api/routers/health.py` và triển khai `/health` cho phase 1 PoC.

Trả trạng thái app và nếu thuận tiện thì thêm kiểm tra nhẹ cho DB. Không làm metrics/observability nâng cao ở bước này.
```

---

## Bước 14.4 — Wiring app chính

### File
- `src/reviewagent/api/main.py`
- `src/reviewagent/api/deps.py`

### Prompt cho AI
```text
Hãy đọc `src/reviewagent/api/main.py` và `src/reviewagent/api/deps.py`, rồi wiring đầy đủ app FastAPI cho phase 1 PoC.

Yêu cầu:
- include các router `submissions`, `decisions`, `health`
- cấu hình dependency cần thiết từ settings và DB session
- app có thể chạy local bằng uvicorn

Không thêm middleware/auth/CORS phức tạp nếu chưa cần cho PoC.
```

---

# PHẦN 15 — Tests

## Bước 15.1 — Test schema

### File
- `tests/unit/test_schemas.py`

### Prompt cho AI
```text
Hãy tạo file `tests/unit/test_schemas.py` cho phase 1 PoC.

Cần test tối thiểu:
- DOI hợp lệ và không hợp lệ
- CMS required fields
- decision enum hợp lệ
- serialization/deserialization của schema chính

Giữ test gọn, trực tiếp, không over-engineer.
```

---

## Bước 15.2 — Test Crossref connector

### File
- `tests/unit/test_crossref_connector.py`

### Prompt cho AI
```text
Hãy tạo file `tests/unit/test_crossref_connector.py` cho phase 1 PoC.

Test các tình huống chính:
- parse response Crossref thành dữ liệu nội bộ đúng
- DOI không tồn tại trả miss hợp lệ
- các field quan trọng map đúng sang CMS-compatible structure

Ưu tiên unit test nhẹ, không phụ thuộc mạng thật nếu tránh được.
```

---

## Bước 15.3 — Test OpenAlex connector

### File
- `tests/unit/test_openalex_connector.py`

### Prompt cho AI
```text
Hãy tạo file `tests/unit/test_openalex_connector.py` cho phase 1 PoC.

Test các tình huống chính:
- parse response OpenAlex đúng
- fallback output có cấu trúc nhất quán với Crossref path
- provenance/source fields đúng

Giữ test đơn giản, tập trung vào mapping dữ liệu.
```

---

## Bước 15.4 — Integration test API

### File
- `tests/integration/test_submissions_api.py`

### Prompt cho AI
```text
Hãy tạo file `tests/integration/test_submissions_api.py` cho phase 1 PoC.

Mục tiêu:
- test endpoint tạo submission
- kiểm response hợp lệ
- kiểm luồng cơ bản từ request đến decision response

Nếu cần mock connector/LLM ở integration test PoC thì mock ở mức nhỏ nhất có thể.
```

---

## Bước 15.5 — Integration test pipeline

### File
- `tests/integration/test_review_pipeline.py`

### Prompt cho AI
```text
Hãy tạo file `tests/integration/test_review_pipeline.py` cho phase 1 PoC.

Cần test:
- input DOI → metadata agent → decision agent → kết quả cuối
- fail-safe path khi metadata thiếu hoặc connector miss

Giữ phạm vi đúng PoC, không kéo vào journal/author/integrity agents.
```

---

# PHẦN 16 — Eval script

## Bước 16.1 — Viết eval cơ bản

### File
- `scripts/eval.py`

### Prompt cho AI
```text
Hãy đọc `scripts/eval.py` và triển khai script đánh giá cơ bản cho phase 1 PoC.

Mục tiêu:
- nhận dataset đầu vào
- chạy pipeline trên từng mẫu
- so sánh decision dự đoán với ground truth nếu có
- tính precision/recall/F1 ở mức cơ bản
- in ra summary dễ đọc

Chưa cần hệ thống eval phức tạp hay dashboard.
```

---

# PHẦN 17 — Docker / README

## Bước 17.1 — Compose tối thiểu

### File
- `docker/docker-compose.yml`

### Prompt cho AI
```text
Hãy đọc `docker/docker-compose.yml` và tinh chỉnh nó cho phase 1 PoC.

Mục tiêu:
- có PostgreSQL dev stack tối thiểu
- nếu hợp lý có thể giữ service app đơn giản
- không thêm các service production như Grafana, Langfuse, worker phức tạp nếu chưa cần

Giữ compose gọn, dễ chạy local.
```

---

## Bước 17.2 — README chạy PoC

### File
- `README.md`

### Prompt cho AI
```text
Hãy đọc `README.md` và viết lại hoặc bổ sung phần hướng dẫn cho phase 1 PoC backend + AI.

README cần có:
- project này đang ở phase nào
- cách cấu hình `.env`
- cách chạy database/dev stack
- cách chạy FastAPI app
- cách gọi `POST /submissions`
- cách chạy test
- cách chạy `scripts/eval.py`

Không thêm tài liệu cho frontend hoặc production deployment.
```

---

# PHẦN 18 — Prompt tổng hợp theo cụm nếu muốn code nhanh hơn

## Cụm A — Foundation + config
```text
Hãy triển khai foundation cho phase 1 PoC backend + AI của project ReviewAgent PTIT.

File cần xử lý trong cụm này:
- `pyproject.toml`
- `.env.example`
- `src/reviewagent/config.py`

Mục tiêu:
- chuẩn hóa dependency tối thiểu
- tạo env variables cần thiết
- triển khai settings bằng pydantic-settings

Không làm frontend, Celery, Redis production, observability, ORCID, journal snapshots.

Sau khi xong, tóm tắt các thay đổi và các cấu hình bắt buộc người dùng phải điền.
```

## Cụm B — Schema + connectors
```text
Hãy triển khai schema và connectors cho phase 1 PoC backend + AI.

File cần xử lý:
- `src/reviewagent/schemas/submission.py`
- `src/reviewagent/schemas/decision.py`
- `src/reviewagent/schemas/cms.py`
- `src/reviewagent/connectors/base.py`
- `src/reviewagent/connectors/crossref.py`
- `src/reviewagent/connectors/openalex.py`

Mục tiêu:
- submission schema tối thiểu cho case có DOI
- decision schema structured output
- CMS grounded có provenance
- connector Crossref và OpenAlex dùng được

Chỉ làm đúng PoC, không thêm logic MVP.
```

## Cụm C — DB + repositories
```text
Hãy triển khai database layer tối thiểu cho phase 1 PoC backend + AI.

File cần xử lý:
- `src/reviewagent/db/session.py`
- `src/reviewagent/db/models/submission.py`
- `src/reviewagent/db/models/publication.py`
- `src/reviewagent/db/models/decision.py`
- `src/reviewagent/db/repositories/submission_repo.py`
- `src/reviewagent/db/repositories/decision_repo.py`

Mục tiêu:
- có async DB session
- lưu được submission
- lưu được publication metadata chuẩn hóa
- lưu được decision

Giữ thiết kế đơn giản, đúng PoC.
```

## Cụm D — Agents + LLM + graph
```text
Hãy triển khai AI pipeline tối thiểu cho phase 1 PoC backend + AI.

File cần xử lý:
- `src/reviewagent/agents/state.py`
- `src/reviewagent/agents/metadata_agent.py`
- `src/reviewagent/agents/decision_agent.py`
- `src/reviewagent/agents/graph.py`
- `src/reviewagent/llm/gateway.py`
- `src/reviewagent/llm/prompts/decision_v1.py`
- `src/reviewagent/llm/calibration.py`

Mục tiêu:
- metadata agent lấy CMS từ Crossref/OpenAlex
- decision agent ra structured decision grounded trên CMS
- graph tuần tự gọi được end-to-end

Không làm multi-agent parallel, journal/author/integrity agents.
```

## Cụm E — API + tests + eval
```text
Hãy triển khai API và test cơ bản cho phase 1 PoC backend + AI.

File cần xử lý:
- `src/reviewagent/api/main.py`
- `src/reviewagent/api/deps.py`
- `src/reviewagent/api/routers/submissions.py`
- `src/reviewagent/api/routers/decisions.py`
- `src/reviewagent/api/routers/health.py`
- `tests/unit/test_schemas.py`
- `tests/unit/test_crossref_connector.py`
- `tests/unit/test_openalex_connector.py`
- `tests/integration/test_submissions_api.py`
- `tests/integration/test_review_pipeline.py`
- `scripts/eval.py`

Mục tiêu:
- app FastAPI chạy được
- endpoint PoC hoạt động
- có unit + integration tests cơ bản
- có eval script cơ bản

Không mở rộng sang reviewer workflow, appeal, reports, metrics.
```

---

# Cách làm thực tế khuyến nghị

## Cách 1 — An toàn, ít lỗi
Gọi AI theo từng bước nhỏ từ 1.1 → 17.2.

## Cách 2 — Nhanh hơn
Gọi theo 5 cụm:
1. Cụm A
2. Cụm B
3. Cụm C
4. Cụm D
5. Cụm E

## Cách 3 — Rất nhanh nhưng dễ lỗi chồng chéo
Cho AI làm một lượt toàn bộ file PoC. Cách này không khuyến nghị nếu repo còn đang định hình.

---

# Checklist hoàn thành phase

- [ ] `pyproject.toml` chạy được dependency tối thiểu
- [ ] `.env.example` đủ biến cho local PoC
- [ ] config load được settings
- [ ] submission schema dùng được
- [ ] CMS schema dùng được
- [ ] decision schema dùng được
- [ ] Crossref connector chạy được
- [ ] OpenAlex connector fallback được
- [ ] DB session + models hoạt động
- [ ] metadata agent hoạt động
- [ ] decision agent hoạt động
- [ ] graph tuần tự chạy end-to-end
- [ ] `POST /submissions` dùng được
- [ ] endpoint đọc decision dùng được
- [ ] `/health` dùng được
- [ ] unit tests cơ bản pass
- [ ] integration tests cơ bản pass
- [ ] `scripts/eval.py` chạy được
- [ ] README đủ hướng dẫn để chạy lại PoC

---

# Gợi ý prompt điều phối tổng quát cho AI ở đầu mỗi phiên

```text
Chúng ta đang triển khai Phase 1 PoC của ReviewAgent PTIT, chỉ làm backend + AI, chưa làm frontend.

Scope PoC hiện tại chỉ gồm:
- nhận submission có DOI
- fetch metadata từ Crossref, fallback OpenAlex
- chuẩn hóa thành CMS có provenance
- chạy decision agent grounded trên CMS
- lưu submission/publication/decision vào database
- trả kết quả qua FastAPI
- có test và eval cơ bản

Không làm trong phiên này:
- frontend/dashboard
- journal quality agents
- ORCID/author disambiguation
- integrity detection
- reviewer queue/appeals/reports
- Celery/Redis production
- observability nâng cao
- Kubernetes/production infra

Mỗi lần chỉ làm đúng phần tôi yêu cầu. Không tự mở rộng scope. Nếu một file đang thiếu context, hãy đọc file đó trước rồi mới sửa.
```
