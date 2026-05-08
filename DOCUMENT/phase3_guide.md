# Phase 3 Production — Hướng dẫn chi tiết

Tài liệu này dành cho developer muốn hiểu toàn bộ Phase 3 Production của ReviewAgent PTIT: từ MVP nội bộ lên hệ thống production với integrity detection, appeal workflow, multi-provider LLM, self-hosted model, Kubernetes, compliance.

---

## Mục lục

1. [Tổng quan nghiệp vụ](#1-tổng-quan-nghiệp-vụ)
2. [Khác biệt chính so với Phase 2](#2-khác-biệt-chính-so-với-phase-2)
3. [Cách chạy toàn bộ Phase 3](#3-cách-chạy-toàn-bộ-phase-3)
4. [Sơ đồ luồng dữ liệu](#4-sơ-đồ-luồng-dữ-liệu)
5. [Chi tiết từng file — vai trò và chức năng](#5-chi-tiết-từng-file)
6. [Thứ tự code và dependency](#6-thứ-tự-code-và-dependency)
7. [Cách test từng phần](#7-cách-test-từng-phần)
8. [Checklist hoàn thành Phase 3](#8-checklist-hoàn-thành-phase-3)

---

## 1. Tổng quan nghiệp vụ

### Bài toán

Sau Phase 2, hệ thống đã chạy được nội bộ: xác minh metadata, kiểm tra tạp chí, đối chiếu tác giả, có reviewer queue. Nhưng để vận hành production cho toàn trường, còn thiếu:

- **Phát hiện gian lận nội dung**: Bài báo có cụm từ tra tấn (tortured phrases), do SCIgen sinh, hay có dấu vân tay ChatGPT không?
- **Kháng nghị (appeal)**: Giảng viên không đồng ý với REJECT → cần quy trình kháng nghị có LLM Opus xử lý.
- **Self-hosted LLM**: Dữ liệu cá nhân (tên, CCCD, email) không được rời khỏi máy chủ Việt Nam → cần PhoGPT-4B hoặc VinaLLaMA-7B on-premises.
- **Multi-provider LLM**: Nếu 1 provider lỗi → tự fallback sang provider khác (Anthropic → Google → OpenAI).
- **Kubernetes**: Cần scale cho 500-1000 bài/tháng, auto-scaling, zero-downtime deploy.
- **Compliance**: Tuân thủ Nghị định 13/2023/NĐ-CP (bảo vệ dữ liệu cá nhân), Luật PDP 2026, quy chế HĐGSNN.
- **CI/CD**: eval gate tự động (F1 không được giảm), canary rollout 5/25/100%.

Phase 3 nâng MVP thành **hệ thống production**: chạy trên Kubernetes PTIT, phục vụ toàn trường, 500-1000 bài/tháng, F1 ≥ 0.92, uptime 99.5%.

### Nguyên tắc cốt lõi (giữ từ Phase 1+2)

- **Grounding trước sinh**
- **Fail safe**: Thiếu evidence → `REVIEW`
- **Deterministic trước stochastic**
- **Parallel trước sequential** (Phase 2)
- **Cache trước fetch** (Phase 2)
- **Audit mọi thứ** (Phase 2)

### Nguyên tắc mới trong Phase 3

- **PII không rời Việt Nam**: Tên đầy đủ, CCCD, email cá nhân phải được xử lý qua self-hosted LLM. Chỉ model on-prem được thấy PII.
- **Defense in depth**: Integrity detection bổ sung 1 lớp bảo vệ nữa ngoài metadata verification.
- **Graceful degradation**: Nếu tất cả cloud LLM provider đều lỗi → fallback xuống self-hosted model → rule-based.
- **Appeal fairness**: Appeal được xử lý bởi model mạnh nhất (Opus), khác với model ra decision ban đầu (Sonnet). Có human-in-the-loop ở cả 2 tầng.
- **Eval gate trước merge**: Mọi PR phải pass eval gate — F1 không được giảm quá 0.01 so với baseline.

### Luồng Phase 3

```
Người dùng gửi DOI + author + affiliation
       │
       ▼
   Validate input
       │
       ▼
   Redis cache check → Cache hit? → Dùng CMS cũ (nếu < 24h)
       │
       ▼
   Router Agent (LangGraph fan-out)
       │
       ├──→ Metadata Agent (Crossref → OpenAlex)
       ├──→ Journal Agent  (MJL + SCImago + DOAJ + Beall + Hijack)
       ├──→ Author Agent   (ORCID + Vietnamese AND, self-hosted LLM)
       └──→ Integrity Agent (MỚI: tortured phrase + SCIgen + ChatGPT fingerprint)
       │
       ▼
   Aggregator Agent — gom kết quả 4 agent
       │
       ▼
   Decision Agent
   (Multi-provider LLM: Anthropic → Google → OpenAI → self-hosted fallback)
   (CoVe + Self-Consistency k=5)
       │
       ├──→ confidence ≥ τ_high (0.95) → APPROVE auto
       ├──→ τ_low (0.70) ≤ confidence < τ_high → REVIEW queue
       └──→ confidence < τ_low → REJECT
       │
       ▼
   Lưu DB + Audit Log (WORM)
       │
       ▼
   Trả JSON response
       │
       ▼
   [Nếu REJECT] → Gửi notification cho người dùng
       │
       ▼
   [Nếu người dùng kháng nghị] → Appeal Agent (Opus)
       │
       ├──→ Uphold appeal → chuyển thành REVIEW
       └──→ Deny appeal → giữ REJECT, có rationale chi tiết
```

### Confidence Score Formula (Phase 3)

```
confidence_raw = (
  0.20 × metadata_score     # Crossref/OpenAlex consistency
  0.20 × journal_score      # Indexing + quartile + not predatory
  0.25 × author_score       # ORCID hoặc AND match
  0.20 × integrity_score    # MỚI: No tortured phrase, no SCIgen, no ChatGPT
  0.15 × policy_score       # Phù hợp quy chế HĐGSNN + QĐ 25
)
confidence_calibrated = sigmoid(A × confidence_raw + B)  # Platt scaling (training trên 500 bài)
```

---

## 2. Khác biệt chính so với Phase 2

| Khía cạnh | Phase 2 MVP | Phase 3 Production |
|-----------|-------------|--------------------|
| **Agents** | 5 agents | 7 agents (+integrity, +appeal) |
| **Integrity** | Không | Tortured phrase 11k+, SCIgen/Mathgen, ChatGPT fingerprint |
| **Appeal** | Không | Appeal workflow với Opus |
| **LLM providers** | OpenRouter (1 provider) | Multi-provider: Anthropic → Google → OpenAI → self-hosted |
| **Self-hosted LLM** | Không | PhoGPT-4B / VinaLLaMA-7B trên A100 + vLLM |
| **Orchestration** | LangGraph parallel | LangGraph + checkpointing + human-in-the-loop |
| **Deploy** | Docker Compose 1 VM | Kubernetes + Helm + ArgoCD GitOps |
| **CI/CD** | CI cơ bản | Eval gate + canary rollout 5/25/100% |
| **Observability** | Langfuse + Prometheus | + OpenTelemetry tracing, Grafana dashboards |
| **Compliance** | Không | NĐ 13/2023, Luật PDP 2026, DPIA |
| **Self-Consistency k** | 3 | 5 |
| **F1 target** | ≥ 0.88 | ≥ 0.92 |
| **Dataset** | 100 bài | 500-1000 bài |
| **Uptime** | 99% | 99.5% |
| **Scale** | ~100 bài/tháng | 500-1000 bài/tháng |
| **Latency** | < 15s | < 20s (integrity work bù cho multi-provider) |
| **Cost** | ≤ 0.05 USD/bài | ≤ 0.05 USD/bài (self-hosted giảm cost cloud) |

---

## 3. Cách chạy toàn bộ Phase 3

### Yêu cầu hệ thống

- Kubernetes cluster (PTIT on-prem hoặc cloud)
- GPU node: 1× NVIDIA A100 40GB (cho self-hosted LLM)
- Helm 3, ArgoCD, kubectl
- PostgreSQL + Redis (managed hoặc trong cluster)
- Docker registry nội bộ
- 16GB RAM cho self-hosted LLM, 8GB cho services khác

### Infrastructure tổng quan

```
                          ┌──────────────────────────┐
                          │    Nginx Ingress          │
                          │    (TLS termination)      │
                          └───────────┬──────────────┘
                                      │
                          ┌───────────▼──────────────┐
                          │    FastAPI Pods (x3)      │
                          │    (HPA: min 3, max 10)  │
                          └───────────┬──────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
    ┌─────────▼────────┐  ┌──────────▼──────────┐  ┌─────────▼────────┐
    │ Celery Workers   │  │ Self-hosted LLM     │  │ PostgreSQL       │
    │ (x3, HPA)        │  │ PhoGPT-4B /         │  │ (Patroni HA)     │
    │                  │  │ VinaLLaMA-7B         │  │                  │
    │                  │  │ vLLM server          │  │                  │
    └──────────────────┘  └─────────────────────┘  └──────────────────┘
              │
    ┌─────────▼────────┐
    │ Redis            │
    │ (Sentinel HA)    │
    └──────────────────┘
```

### Bước 1: Tạo Kubernetes namespace và secrets

```bash
kubectl create namespace reviewagent-production

# Tạo secrets
kubectl create secret generic reviewagent-secrets \
  --from-literal=llm-api-key-anthropic=<key> \
  --from-literal=llm-api-key-google=<key> \
  --from-literal=llm-api-key-openai=<key> \
  --from-literal=database-url=<url> \
  --from-literal=redis-url=<url> \
  --from-literal=audit-secret-key=<random-64-char> \
  -n reviewagent-production
```

### Bước 2: Deploy Helm chart

```bash
cd k8s/helm/reviewagent

# Cài đặt
helm upgrade --install reviewagent . \
  --namespace reviewagent-production \
  --values values-production.yaml \
  --set image.tag=v3.0.0 \
  --wait
```

### Bước 3: Cấu hình ArgoCD GitOps

```bash
# ArgoCD tự sync từ git repo
kubectl apply -f k8s/argocd/reviewagent-app.yaml
```

### Bước 4: Deploy self-hosted LLM

```bash
# Deploy vLLM với PhoGPT-4B
kubectl apply -f k8s/vllm/vllm-deployment.yaml
kubectl apply -f k8s/vllm/vllm-service.yaml

# Kiểm tra
curl http://vllm.reviewagent-production.svc.cluster.local:8000/health
# {"status": "ok", "model": "phogpt-4b"}
```

### Bước 5: Seed snapshots vào production DB

```bash
kubectl exec -it deployment/reviewagent-api -- \
  python scripts/seed_snapshots.py --all
```

### Bước 6: Chạy migration

```bash
kubectl exec -it deployment/reviewagent-api -- \
  alembic upgrade head
```

### Bước 7: Verify production

```bash
# Health
curl https://reviewagent.ptit.edu.vn/health
# {"status": "ok", "database": "ok", "redis": "ok", "vllm": "ok"}

# Metrics
curl https://reviewagent.ptit.edu.vn/metrics

# Submission
curl -X POST https://reviewagent.ptit.edu.vn/submissions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{"doi": "10.1109/5.771073", "user_claimed_author": "Nguyen Van A"}'
```

---

## 4. Sơ đồ luồng dữ liệu

```
                              ┌─────────────────────────┐
                              │     HTTP Request          │
                              │  POST /submissions       │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  api/middleware.py       │
                              │  - JWT Auth (PTIT SSO)   │
                              │  - Rate limiting         │
                              │  - Request logging       │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  api/routers/            │
                              │  submissions.py          │
                              │  - Validate input         │
                              │  - Tạo Submission record  │
                              │  - Dispatch Celery task   │
                              └───────────┬─────────────┘
                                          │
                          ┌───────────────┼───────────────┐
                          │ Celery Worker                │
                          │                               │
                          │  ┌─────────────────────────┐  │
                          │  │ agents/graph.py          │  │
                          │  │ LangGraph StateGraph      │  │
                          │  │ + Checkpointing           │  │
                          │  │ + Human-in-the-loop       │  │
                          │  │                          │  │
                          │  │  ┌────────────────────┐  │  │
                          │  │  │ router_agent        │  │  │
                          │  │  │ → Fan-out 4 nhánh   │  │  │
                          │  │  └────────┬───────────┘  │  │
                          │  │           │              │  │
                          │  │  ┌────────┼──────────┐   │  │
                          │  │  │        │          │   │  │
                          │  │  ▼        ▼          ▼   │  │
                          │  │  ┌─────┐┌─────┐┌──────┐  │  │
                          │  │  │Meta ││Jour ││Author│   │  │
                          │  │  │data ││nal  ││      │   │  │
                          │  │  └──┬──┘└──┬──┘└──┬───┘   │  │
                          │  │     │      │      │      │  │
                          │  │     ▼      │      │      │  │
                          │  │  ┌────────┐│      │      │  │
                          │  │  │Integri││      │      │  │
                          │  │  │ty     ││      │      │  │
                          │  │  │Agent  ││      │      │  │
                          │  │  └──┬────┘│      │      │  │
                          │  │     │     │      │      │  │
                          │  │  ┌──┴─────┴──────┴──┐   │  │
                          │  │  │ aggregator_agent  │   │  │
                          │  │  └────────┬─────────┘   │  │
                          │  │           │             │  │
                          │  │  ┌────────▼─────────┐   │  │
                          │  │  │ decision_agent    │   │  │
                          │  │  │ Multi-provider    │   │  │
                          │  │  │ Anthropic →       │   │  │
                          │  │  │ Google →          │   │  │
                          │  │  │ OpenAI →          │   │  │
                          │  │  │ Self-hosted       │   │  │
                          │  │  └────────┬─────────┘   │  │
                          │  └───────────┼─────────────┘  │
                          └───────────────┼───────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  DB + Audit + Cache      │
                              │  - PostgreSQL            │
                              │  - Redis cache           │
                              │  - WORM Audit log        │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  Observability           │
                              │  - OpenTelemetry traces  │
                              │  - Prometheus metrics    │
                              │  - Grafana dashboards    │
                              │  - Langfuse LLM tracing  │
                              └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  HTTP Response           │
                              │  + Notification          │
                              │  (email/Slack nếu REJECT)│
                              └─────────────────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │  Appeal Flow (nếu có)    │
                              │                          │
                              │  POST /appeals           │
                              │  → Appeal Agent (Opus)   │
                              │  → Uphold / Deny         │
                              │  → Audit log             │
                              │  → Notification          │
                              └─────────────────────────┘
```

---

## 5. Chi tiết từng file

### 5.1. Layer Integrity (MỚI HOÀN TOÀN)

Đây là **Layer 4** — phát hiện dấu hiệu gian lận học thuật trong nội dung bài báo.

#### `src/reviewagent/integrity/tortured_phrase.py` (MỚI)

**Vai trò**: Phát hiện "tortured phrases" — cụm từ bị paraphrase ngớ ngẩn để tránh plagiarism detection.

**Cơ sở dữ liệu**: 11,000+ cụm từ từ Guillaume Cabanac et al. (2021).

**Thuật toán**:
```python
TORTURED_PHRASES = load_phrase_dict()  # {"flag to consider" → "flag to consider", ...}

class TorturedPhraseDetector:
    def detect(self, text: str) -> TorturedPhraseResult:
        """
        Quét abstract + title của bài báo.
        Dùng Aho-Corasick automaton để multi-pattern matching O(n + m).
        """
        matches = self._automaton.search(text.lower())
        return TorturedPhraseResult(
            has_tortured_phrases=len(matches) > 0,
            matches=[(phrase, count) for phrase, count in matches],
            density=len(matches) / len(text.split()),  # Mật độ cụm từ nghi ngờ
            score=self._compute_score(matches),
        )
```

**Scoring**:
- 0 match → score = 1.0 (sạch)
- 1-2 matches → score = 0.5 (nghi ngờ nhẹ)
- 3-5 matches → score = 0.2 (nghi ngờ cao)
- \> 5 matches → score = 0.0 (gần như chắc chắn gian lận)

**Ví dụ tortured phrases**:
| Cụm gốc thật | Tortured phrase (bị SCIgen đổi) |
|-------------|--------------------------------|
| "signal to noise ratio" | "flag to clamor proportion" |
| "random forest" | "irregular woodland" |
| "support vector machine" | "bolster vector machine" |
| "artificial intelligence" | "counterfeit consciousness" |

---

#### `src/reviewagent/integrity/scigen_detector.py` (MỚI)

**Vai trò**: Phát hiện bài báo sinh tự động bởi SCIgen, Mathgen, hoặc Physgen.

**Dấu hiệu nhận biết**:
1. **Tác giả ảo**: Tên tác giả khớp pattern của SCIgen (kết hợp ngẫu nhiên từ dictionary cố định)
2. **Reference ảo**: References trỏ đến author/title không tồn tại
3. **Cấu trúc câu lặp**: Phân phối câu có pattern đều bất thường (thống kê entropy)
4. **Figure/table giả**: Reference đến figure/table không tồn tại trong text

```python
class SCIgenDetector:
    def detect(self, text: str, authors: list[str], references: list[str]) -> SCIgenResult:
        scores = {}
        scores["author_pattern"] = self._check_author_patterns(authors)
        scores["reference_validity"] = self._check_references(references)
        scores["sentence_entropy"] = self._check_sentence_patterns(text)
        scores["fake_figures"] = self._check_figure_refs(text)

        overall = sum(scores.values()) / len(scores)
        return SCIgenResult(
            is_generated=overall < 0.3,
            sub_scores=scores,
            flags=self._build_flags(scores),
        )
```

---

#### `src/reviewagent/integrity/chatgpt_fingerprint.py` (MỚI)

**Vai trò**: Phát hiện văn bản có khả năng cao do ChatGPT/LLM sinh ra.

**Dấu hiệu**:
1. **Overuse of transitions**: "However", "Moreover", "Furthermore", "In addition" với tần suất cao bất thường
2. **Zero perplexity burst**: Đoạn văn có perplexity thấp bất thường (LLM text thường "quá mượt")
3. **Template phrases**: Các cụm như "As an AI language model", "It is important to note that"
4. **Bursted vocabulary**: Từ vựng đa dạng bất thường so với academic writing thông thường

```python
class ChatGPTFingerprintDetector:
    def detect(self, text: str) -> ChatGPTFingerprintResult:
        scores = {}
        scores["transition_density"] = self._transition_density(text)
        scores["perplexity_burst"] = self._perplexity_burst(text)
        scores["template_phrases"] = self._template_match(text)
        scores["vocabulary_diversity"] = self._ttr_score(text)

        return ChatGPTFingerprintResult(
            likely_ai_generated=self._aggregate(scores) > 0.7,
            sub_scores=scores,
            evidence=self._collect_evidence(text, scores),
        )
```

---

#### `src/reviewagent/agents/integrity_agent.py` (MỚI)

**Vai trò**: **Agent Layer 4** — chạy tất cả detector, gom kết quả thành IntegrityCheckResult.

```python
class IntegrityAgent:
    def __init__(self):
        self._tortured = TorturedPhraseDetector()
        self._scigen = SCIgenDetector()
        self._chatgpt = ChatGPTFingerprintDetector()

    async def run(self, state: ReviewState) -> IntegrityCheckResult:
        text = self._extract_text(state.cms)

        results = await asyncio.gather(
            asyncio.to_thread(self._tortured.detect, text),
            asyncio.to_thread(self._scigen.detect, text, ...),
            asyncio.to_thread(self._chatgpt.detect, text),
        )

        integrity_score = self._combine_scores(results)
        flags = self._collect_flags(results)

        return IntegrityCheckResult(
            integrity_score=integrity_score,
            tortured_phrase=results[0],
            scigen=results[1],
            chatgpt_fingerprint=results[2],
            flags=flags,
        )
```

**Scoring tổng hợp**:
```
integrity_score = min(tortured.score, scigen.score, chatgpt.score)
```

Dùng `min` thay vì trung bình — nếu bất kỳ detector nào flag, điểm giảm mạnh (defense in depth).

---

### 5.2. Layer Appeal (MỚI)

#### `src/reviewagent/agents/appeal_agent.py` (MỚI)

**Vai trò**: Xử lý kháng nghị khi giảng viên không đồng ý với REJECT.

**Nguyên tắc**:
- Appeal dùng model **mạnh nhất** (Claude Opus 4.7) — khác với model decision ban đầu (Sonnet 4.6)
- Appeal đọc **toàn bộ evidence** từ lần review đầu + lý do kháng nghị của người dùng
- Output: `UPHOLD` (chấp nhận kháng nghị, chuyển thành REVIEW) hoặc `DENY` (bác bỏ, giữ REJECT)

```python
class AppealAgent:
    async def run(self, original_decision: DecisionResult,
                  appeal_reason: str, evidence_panel: list[Evidence]) -> AppealResult:
        """
        Gọi Claude Opus 4.7 với prompt appeal.
        Yêu cầu model:
        1. Đọc lại evidence gốc (không hallucinate thêm)
        2. Đánh giá lý do kháng nghị của người dùng
        3. Trả UPHOLD nếu lý do hợp lệ + có evidence hỗ trợ
        4. Trả DENY nếu lý do không đủ thuyết phục
        """
        prompt = build_appeal_prompt(original_decision, appeal_reason, evidence_panel)
        response = await self._gateway.call_opus(prompt)
        return self._parse_appeal(response)
```

**Appeal workflow**:
```
REJECT decision
    │
    ▼
Người dùng nộp appeal (lý do + evidence bổ sung) trong 7 ngày
    │
    ▼
Appeal Agent (Opus) xử lý
    │
    ├──→ UPHOLD: chuyển submission sang REVIEW queue
    │        → Reviewer xem lại với context appeal
    │        → Decision cuối cùng có thể là APPROVE hoặc giữ REJECT
    │
    └──→ DENY: giữ REJECT
             → Gửi rationale chi tiết cho người dùng
             → Người dùng có thể escalate lên HĐGSNN (ngoài hệ thống)
```

#### `src/reviewagent/api/routers/appeals.py` (MỚI)

**Vai trò**: Endpoint cho appeal workflow.

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/appeals` | POST | Nộp kháng nghị cho 1 decision |
| `/appeals/{appeal_id}` | GET | Xem trạng thái kháng nghị |
| `/appeals/{appeal_id}/cancel` | POST | Rút kháng nghị |

---

### 5.3. Multi-Provider LLM (NÂNG CẤP)

#### `src/reviewagent/llm/gateway.py` (NÂNG CẤP)

**Vai trò**: Multi-provider LLM gateway với fallback chain.

**Thứ tự fallback**:
```
1. Anthropic Claude Sonnet 4.6  (primary — provider chính)
   ↓ (nếu lỗi)
2. Google Gemini 2.5 Pro        (fallback 1)
   ↓ (nếu lỗi)
3. OpenAI GPT-4o                (fallback 2)
   ↓ (nếu lỗi)
4. Self-hosted PhoGPT-4B        (fallback cuối, on-prem, không cost API)
   ↓ (nếu lỗi)
5. Rule-based decision          (deterministic fallback tuyệt đối)
```

```python
class MultiProviderGateway:
    PROVIDERS = [
        ("anthropic", self._call_anthropic),
        ("google", self._call_google),
        ("openai", self._call_openai),
        ("self_hosted", self._call_vllm),
    ]

    async def generate_decision(self, system_prompt: str, user_prompt: str) -> DecisionResult:
        last_error = None
        for provider_name, call_fn in self.PROVIDERS:
            try:
                logger.info(f"Calling LLM: {provider_name}")
                result = await call_fn(system_prompt, user_prompt)
                result["llm_provider"] = provider_name  # Gắn provenance
                return self._parse_decision(result)
            except Exception as e:
                logger.warning(f"LLM {provider_name} failed: {e}")
                last_error = e
                continue

        # Tất cả provider đều fail → rule-based
        logger.error(f"All LLM providers failed. Last error: {last_error}")
        return self._rule_based_decision()
```

**Circuit breaker**: Nếu 1 provider fail 5 lần trong 60s → tạm ngắt 120s (tránh gọi liên tục vào provider lỗi).

---

### 5.4. Self-Hosted LLM (MỚI)

#### `src/reviewagent/llm/self_hosted.py` (MỚI)

**Vai trò**: Client gọi self-hosted LLM qua vLLM server.

**Lý do self-hosted**: Luật PDP yêu cầu dữ liệu cá nhân (tên, CCCD) không rời khỏi máy chủ Việt Nam.

**Model đề xuất**:
| Model | Kích thước | VRAM | Use case |
|-------|-----------|------|----------|
| **PhoGPT-4B** | 4B params | ~8GB FP16 | AND Pipeline — name matching, embedding |
| **VinaLLaMA-7B** | 7B params | ~14GB FP16 | Decision fallback (chất lượng khá hơn PhoGPT) |

**Triển khai**: vLLM server trên pod GPU (A100 40GB), serve qua REST API `/v1/chat/completions`.

```python
class SelfHostedLLMClient:
    def __init__(self, base_url: str = "http://vllm.reviewagent-production.svc.cluster.local:8000"):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def chat(self, messages: list[dict], model: str = "phogpt-4b") -> str:
        response = await self._client.post("/v1/chat/completions", json={
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        })
        return response.json()["choices"][0]["message"]["content"]
```

**Use cases cho self-hosted**:
1. **AND Pipeline**: Chuẩn hóa tên tiếng Việt, sinh vector embedding
2. **PII processing**: Khi cần xử lý tên đầy đủ, email, CCCD
3. **Decision fallback**: Khi tất cả cloud provider đều lỗi
4. **Appeal**: Có thể dùng self-hosted model song song với Opus, so sánh kết quả

---

### 5.5. CI/CD Pipeline — Eval Gate + Canary

#### `.github/workflows/ci.yml` (NÂNG CẤP)

```yaml
name: CI Pipeline
on:
  pull_request:
    branches: [main, production]

jobs:
  lint-and-type:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ruff lint
        run: ruff check src/
      - name: Mypy type check
        run: mypy src/reviewagent --strict

  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: ...
    steps:
      - run: pytest tests/unit/ -v --cov --cov-report=xml

  eval-gate:
    needs: [unit-tests]
    runs-on: ubuntu-latest
    steps:
      - name: Run evaluation
        run: python scripts/eval.py --dataset tests/gold_dataset/seed_500.json --phase3
      - name: Check F1 gate
        run: |
          F1=$(jq '.f1_score' eval_report.json)
          if (( $(echo "$F1 < 0.91" | bc -l) )); then
            echo "F1 $F1 < 0.91 — EVAL GATE FAILED"
            exit 1
          fi
          echo "F1 $F1 >= 0.91 — EVAL GATE PASSED"
```

**Canary rollout strategy**:
```
Deploy v3.1.0:
  1. Deploy 5% traffic → wait 5 min
     → Check error rate, latency p95, decision distribution
     → OK?
  2. Deploy 25% traffic → wait 10 min
     → Check same metrics
     → OK?
  3. Deploy 100% traffic → done
     → Nếu bất kỳ bước nào fail → auto-rollback
```

---

### 5.6. Kubernetes Manifests (MỚI)

#### `k8s/helm/reviewagent/` (MỚI — toàn bộ thư mục)

Cấu trúc Helm chart:
```
k8s/helm/reviewagent/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── templates/
│   ├── deployment-api.yaml
│   ├── deployment-worker.yaml
│   ├── deployment-vllm.yaml
│   ├── service-api.yaml
│   ├── service-vllm.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── hpa-api.yaml
│   ├── hpa-worker.yaml
│   └── servicemonitor.yaml
```

#### `k8s/argocd/reviewagent-app.yaml` (MỚI)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: reviewagent-production
spec:
  project: default
  source:
    repoURL: https://github.com/Hieuvu4438/V.A.S.P.git
    targetRevision: production
    path: k8s/helm/reviewagent
  destination:
    server: https://kubernetes.default.svc
    namespace: reviewagent-production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

### 5.7. Observability Nâng Cao

#### `src/reviewagent/observability/tracing.py` (NÂNG CẤP)

**Thay đổi**: Chuyển từ Langfuse standalone sang OpenTelemetry + Langfuse.

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

tracer = trace.get_tracer("reviewagent")

class TracedLLMCall:
    async def __call__(self, provider: str, model: str, prompt: str):
        with tracer.start_as_current_span(f"llm.{provider}") as span:
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.prompt_tokens", len(prompt))
            result = await self._call(prompt)
            span.set_attribute("llm.completion_tokens", len(result))
            span.set_attribute("llm.cost_usd", self._cost)
            return result
```

#### `src/reviewagent/observability/metrics.py` (NÂNG CẤP)

**Thêm metric**:
```python
# Decision distribution by label
decision_counter = Counter("reviewagent_decisions_total", "Total decisions", ["label", "provider"])

# Appeal statistics
appeal_counter = Counter("reviewagent_appeals_total", "Total appeals", ["result"])

# Self-hosted LLM
vllm_latency = Histogram("reviewagent_vllm_duration_seconds", "vLLM latency")
vllm_queue_size = Gauge("reviewagent_vllm_queue_size", "vLLM request queue")

# Integrity detection
integrity_flag_counter = Counter("reviewagent_integrity_flags_total", "Integrity flags", ["detector"])
```

**Grafana dashboards**: Ít nhất 4 dashboard:
1. **API Overview**: Throughput, latency, error rate, status codes
2. **LLM Performance**: Calls, tokens, cost, latency per provider, circuit breaker status
3. **Decision Analytics**: APPROVE/REVIEW/REJECT distribution, confidence histogram, appeal rate
4. **Integrity Detection**: Flag rate per detector, correlation với decision label

---

### 5.8. Compliance (MỚI)

#### `src/reviewagent/compliance/dpia.py` (MỚI)

**Vai trò**: Data Protection Impact Assessment — ghi log xử lý dữ liệu cá nhân.

```python
class DPIAAudit:
    def log_pii_access(self, actor: str, data_type: str, purpose: str):
        """
        Ghi log mỗi khi dữ liệu cá nhân được truy cập.
        data_type: "full_name" | "email" | "cccd" | "orcid"
        purpose: "author_verification" | "appeal" | "audit"
        """

    def verify_pii_local_only(self) -> bool:
        """
        Kiểm tra PII chưa bao giờ được gửi lên cloud LLM.
        Dùng để audit compliance.
        """
```

#### `src/reviewagent/api/routers/reports.py` (MỚI)

**Vai trò**: Endpoint xuất báo cáo — phục vụ HĐGSNN.

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/reports/hdgsnn` | GET | Xuất báo cáo theo mẫu HĐGSNN (Excel) |
| `/reports/monthly` | GET | Báo cáo thống kê hàng tháng |
| `/reports/compliance` | GET | Báo cáo compliance (PII audit) |

---

### 5.9. Reflexion Loop (MỚI)

#### `src/reviewagent/agents/reflexion.py` (MỚI)

**Vai trò**: Học từ reviewer overrides để cải thiện prompt/rule.

**Cơ chế**:
```
1. Mỗi tháng, lọc tất cả các case reviewer sửa decision
2. Phân tích pattern: sai ở agent nào? thiếu evidence gì?
3. Đề xuất cải thiện:
   - Rule-based: thêm rule mới nếu pattern lặp lại ≥ 3 lần
   - Prompt: thêm few-shot example từ case sai
4. Sinh báo cáo "lessons learned" → team review → apply
```

**Đây không phải auto-ML training** — chỉ là tool hỗ trợ team cải thiện hệ thống thủ công. Không tự động modify prompt/model.

---

## 6. Thứ tự code và dependency

### Giai đoạn 1: Integrity detectors (files 1-3)

```
1. integrity/tortured_phrase.py
   → Không phụ thuộc code khác (chỉ cần CSV dictionary)
   → Core: Aho-Corasick automaton multi-pattern matching

2. integrity/scigen_detector.py
   → Không phụ thuộc code khác
   → Core: Statistical feature extraction

3. integrity/chatgpt_fingerprint.py
   → Không phụ thuộc code khác
   → Core: Text feature extraction (perplexity, TTR)
```

### Giai đoạn 2: Self-Hosted LLM (files 4-5)

```
4. llm/self_hosted.py
   → Phụ thuộc: config.py
   → vLLM client đơn giản

5. Nâng cấp llm/gateway.py → Multi-provider
   → Phụ thuộc: self_hosted.py, config.py
   → Fallback chain: Anthropic → Google → OpenAI → Self-hosted → Rule-based
```

### Giai đoạn 3: Integrity Agent (file 6)

```
6. agents/integrity_agent.py
   → Phụ thuộc: integrity/*.py, agents/state.py, schemas (mới)
```

### Giai đoạn 4: Appeal Agent + Workflow (files 7-9)

```
7. llm/prompts/appeal_v1.py
   → Prompt cho Opus xử lý kháng nghị

8. agents/appeal_agent.py
   → Phụ thuộc: llm/gateway.py, schemas/decision.py

9. api/routers/appeals.py
   → Phụ thuộc: agents/appeal_agent.py, db/repositories/*.py, audit/worm_logger.py
```

### Giai đoạn 5: Schemas mở rộng (files 10-12)

```
10. schemas/integrity.py
    → IntegrityCheckResult

11. schemas/appeal.py
    → AppealRequest, AppealResult

12. Nâng cấp schemas/cms.py → v3.0
    → Thêm integrity fields
```

### Giai đoạn 6: Database mở rộng (files 13-14)

```
13. db/models/integrity.py
14. db/models/appeal.py
```

### Giai đoạn 7: Observability nâng cao (files 15-17)

```
15. Nâng cấp observability/tracing.py → OpenTelemetry
16. Nâng cấp observability/metrics.py → Thêm metric
17. Cấu hình Grafana dashboards (JSON)
```

### Giai đoạn 8: Compliance (files 18-19)

```
18. compliance/dpia.py
19. api/routers/reports.py
```

### Giai đoạn 9: Agents nâng cấp (files 20-24)

```
20. agents/reflexion.py
21. Nâng cấp agents/state.py → Thêm integrity_result
22. Nâng cấp agents/aggregator_agent.py → Gom 4 agent (thêm integrity)
23. Nâng cấp agents/decision_agent.py → SC k=5, τ_high=0.95
24. Nâng cấp agents/graph.py → Thêm integrity agent vào fan-out
```

### Giai đoạn 10: K8s + CI/CD (files 25-30)

```
25. k8s/helm/reviewagent/ (toàn bộ chart)
26. k8s/argocd/reviewagent-app.yaml
27. k8s/vllm/ (deployment + service)
28. .github/workflows/ci.yml nâng cấp (eval gate)
29. .github/workflows/cd.yml (canary deploy)
30. docker/Dockerfile.api + Dockerfile.worker
```

### Giai đoạn 11: Tests + Eval (files 31-36)

```
31. tests/unit/test_tortured_phrase.py
32. tests/unit/test_scigen_detector.py
33. tests/unit/test_chatgpt_fingerprint.py
34. tests/unit/test_appeal_agent.py
35. tests/integration/test_integrity_pipeline.py
36. tests/gold_dataset/seed_500.json
```

---

## 7. Cách test từng phần

### Test 1: Integrity detectors (offline)

```bash
# Test tortured phrase detector
python -c "
from reviewagent.integrity.tortured_phrase import TorturedPhraseDetector
d = TorturedPhraseDetector()
result = d.detect('We use irregular woodland for classification. The flag to clamor proportion is high.')
print(f'Found: {len(result.matches)} tortured phrases')
for phrase, count in result.matches:
    print(f'  - {phrase}: {count}')
# Found: 2 tortured phrases
#   - irregular woodland: 1
#   - flag to clamor proportion: 1
"

# Test SCIgen detector
python -c "
from reviewagent.integrity.scigen_detector import SCIgenDetector
d = SCIgenDetector()
# Test với abstract từ bài SCIgen thật
result = d.detect(scigen_abstract, scigen_authors, scigen_refs)
print(f'Is generated: {result.is_generated}')
"

# Test ChatGPT fingerprint
python -c "
from reviewagent.integrity.chatgpt_fingerprint import ChatGPTFingerprintDetector
d = ChatGPTFingerprintDetector()
result = d.detect('However, it is important to note that... Moreover... Furthermore...')
print(f'AI probability: {result.likely_ai_generated}')
"
```

### Test 2: Multi-provider LLM

```bash
# Test fallback chain
python -c "
from reviewagent.llm.gateway import MultiProviderGateway
# Setup: chỉ bật self-hosted, tắt cloud
g = MultiProviderGateway(providers=['self_hosted'])
result = await g.generate_decision('...', '...')
print(f'Provider used: {result.llm_provider}')
# → 'self_hosted'
"
```

### Test 3: Self-hosted LLM (cần GPU)

```bash
# Local test với PhoGPT-4B (CPU fallback)
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "phogpt-4b", "messages": [{"role": "user", "content": "Chuẩn hóa tên: Nguyễn Văn A"}]}'
```

### Test 4: Appeal workflow

```bash
# Nộp appeal
curl -X POST http://localhost:8000/appeals \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{
    "decision_id": "...",
    "reason": "Tôi là tác giả thứ 3 của bài báo này, ORCID của tôi là 0000-0002-...",
    "additional_evidence": {"orcid": "0000-0002-..."}
  }'

# Kiểm tra kết quả
curl http://localhost:8000/appeals/{appeal_id}
```

### Test 5: Eval gate

```bash
# Eval với 500 bài (bắt buộc pass F1 ≥ 0.91)
python scripts/eval.py \
  --dataset tests/gold_dataset/seed_500.json \
  --phase3 \
  --output eval_report.json \
  --fail-under 0.91

# Output:
# Total: 500
# Correct: 460
# Precision: 0.925
# Recall: 0.918
# F1: 0.921
# Cost: $21.37 (0.043 USD/bài)
# EVAL GATE: PASSED (F1 0.921 ≥ 0.91)
```

### Test 6: K8s deployment (cần cluster)

```bash
# Verify deployment
kubectl get pods -n reviewagent-production
kubectl get hpa -n reviewagent-production
kubectl logs -f deployment/reviewagent-api

# Port-forward để test local
kubectl port-forward svc/reviewagent-api 8000:8000 -n reviewagent-production
curl http://localhost:8000/health
```

### Test 7: Canary rollout

```bash
# Monitoring trong quá trình canary
watch -n 5 '
  curl -s https://reviewagent.ptit.edu.cn/metrics | grep reviewagent_
'

# Theo dõi error rate và latency
kubectl logs -f deployment/reviewagent-api-v3.1.0-canary -n reviewagent-production
```

---

## 8. Checklist hoàn thành Phase 3

### Integrity
- [ ] `integrity/tortured_phrase.py` — Aho-Corasick, 11k+ phrases, score < 1s
- [ ] `integrity/scigen_detector.py` — 4 detection signals, score aggregation
- [ ] `integrity/chatgpt_fingerprint.py` — Transition density, perplexity, TTR
- [ ] `agents/integrity_agent.py` — Gom 3 detector, min-score aggregation

### Self-Hosted LLM
- [ ] `llm/self_hosted.py` — vLLM client, PhoGPT-4B + VinaLLaMA-7B
- [ ] `k8s/vllm/` — Deployment + Service cho GPU pod
- [ ] PII processing: tên, email, CCCD qua self-hosted (không qua cloud)

### Multi-Provider LLM
- [ ] `llm/gateway.py` nâng cấp — Fallback chain 4 providers
- [ ] Circuit breaker: 5 lỗi/60s → ngắt 120s
- [ ] Provenance tracking: `llm_provider` trong DecisionResult

### Appeal
- [ ] `llm/prompts/appeal_v1.py` — Prompt cho Opus
- [ ] `agents/appeal_agent.py` — Appeal logic với Opus
- [ ] `api/routers/appeals.py` — CRUD appeals
- [ ] Appeal workflow: UPHOLD → REVIEW queue, DENY → rationale

### Schemas
- [ ] `schemas/integrity.py` — IntegrityCheckResult
- [ ] `schemas/appeal.py` — AppealRequest, AppealResult
- [ ] `schemas/cms.py` v3.0

### Database
- [ ] `db/models/integrity.py` — Bảng integrity_checks
- [ ] `db/models/appeal.py` — Bảng appeals

### Agents
- [ ] `agents/state.py` nâng cấp — integrity_result
- [ ] `agents/aggregator_agent.py` nâng cấp — 4 agent input
- [ ] `agents/decision_agent.py` nâng cấp — SC k=5, τ_high=0.95
- [ ] `agents/graph.py` nâng cấp — Fan-out 4 nhánh
- [ ] `agents/reflexion.py` — Lessons learned tool

### Observability
- [ ] OpenTelemetry tracing (FastAPI + httpx + LLM)
- [ ] Prometheus metrics (integrity flags, appeal stats, vLLM queue)
- [ ] Grafana dashboards (API, LLM, Decision, Integrity)
- [ ] Alerts: error rate > 5%, latency p95 > 30s, eval F1 drop > 0.01

### Compliance
- [ ] `compliance/dpia.py` — PII access audit
- [ ] `api/routers/reports.py` — HĐGSNN + monthly + compliance reports
- [ ] DPIA document (theo NĐ 13/2023/NĐ-CP)

### K8s
- [ ] Helm chart (`k8s/helm/reviewagent/`)
- [ ] ArgoCD application (`k8s/argocd/reviewagent-app.yaml`)
- [ ] vLLM deployment (`k8s/vllm/`)
- [ ] HPA: API min 3 max 10, worker min 3 max 20
- [ ] NetworkPolicy — chỉ self-hosted LLM được truy cập PII

### CI/CD
- [ ] CI: lint → type-check → unit tests → eval gate (F1 ≥ 0.91)
- [ ] CD: canary rollout 5% → 25% → 100%
- [ ] Auto-rollback nếu error rate tăng > 2× baseline

### Tests
- [ ] `tests/unit/test_tortured_phrase.py` — (≥ 5 tests)
- [ ] `tests/unit/test_scigen_detector.py` — (≥ 3 tests)
- [ ] `tests/unit/test_chatgpt_fingerprint.py` — (≥ 3 tests)
- [ ] `tests/unit/test_appeal_agent.py` — (≥ 3 tests)
- [ ] `tests/integration/test_integrity_pipeline.py` — (≥ 3 tests)
- [ ] `tests/integration/test_multi_provider_fallback.py` — (≥ 2 tests)
- [ ] `tests/gold_dataset/seed_500.json` — 500 bài annotated

### Chỉ số đánh giá
- [ ] F1 ≥ 0.92 trên gold dataset 500 bài
- [ ] Latency trung bình < 20s
- [ ] Cost ≤ 0.05 USD/bài
- [ ] Uptime 99.5% (monitoring 3 tháng)
- [ ] Appeal xử lý trong 24h
- [ ] Integrity false-positive rate < 5%

---

## Phụ lục: Câu hỏi thường gặp

**Q: Tại sao cần self-hosted LLM thay vì dùng hoàn toàn cloud API?**
A: Hai lý do chính: (1) Nghị định 13/2023/NĐ-CP và Luật PDP 2026 yêu cầu dữ liệu cá nhân (tên, CCCD, email) không được chuyển ra nước ngoài nếu chưa được sự đồng ý rõ ràng; (2) Cost — self-hosted model dùng GPU on-prem, không mất phí API call, giúp giảm cost/bài. Tuy nhiên, cloud LLM vẫn dùng cho decision chính vì chất lượng cao hơn.

**Q: Multi-provider LLM có thực sự cần 4 providers không?**
A: Production cần defense in depth cho LLM. Nếu Anthropic downtime (đã từng xảy ra), hệ thống không thể ngừng hoàn toàn. Fallback chain đảm bảo graceful degradation — chuyển dần xuống model yếu hơn nhưng không bao giờ mất hoàn toàn chức năng decision.

**Q: Tại sao SC k=5 mà không phải k=3 như Phase 2?**
A: k=5 cho majority vote chính xác hơn (giảm variance) và vẫn trong budget — self-hosted model bù đắp cost cloud. Phase 3 có thêm integrity agent → confidence formula phức tạp hơn → cần nhiều sample hơn để ổn định.

**Q: Appeal không sợ người dùng lạm dụng (submit appeal hàng loạt) sao?**
A: Có 3 cơ chế: (1) Rate limit — 1 appeal/submission, (2) Appeal tốn cost (Opus — model đắt nhất), (3) Appeal không có nghĩa là auto-approve — Opus vẫn đánh giá khách quan. Nếu appeal bị DENY, giữ REJECT.

**Q: Reflexion loop có phải là auto-ML training không?**
A: Không. Reflexion chỉ là công cụ phân tích pattern từ reviewer overrides để team cải thiện prompt/rule **thủ công**. Không tự động modify model weight hay prompt.

**Q: CI/CD eval gate có làm chậm development không?**
A: Eval gate (~5-10 phút với 500 bài) chạy sau unit tests. Chỉ block merge nếu F1 giảm > 0.01. Đây là safety net, không phải bottleneck — đảm bảo mọi thay đổi đều duy trì hoặc cải thiện chất lượng.

**Q: Tại sao τ_high = 0.95 mà không phải 0.90 như Phase 2?**
A: Phase 3 có thêm integrity signals → confidence chính xác hơn → có thể nâng ngưỡng auto-approve. Mục tiêu: giảm false positive xuống dưới 5% cho auto-approve. Các case dưới 0.95 vẫn vào REVIEW queue — an toàn hơn cho production.

**Q: Khi nào thì escalate appeal lên HĐGSNN?**
A: Khi appeal bị DENY và người dùng vẫn không đồng ý. Hệ thống cung cấp toàn bộ evidence + audit log để người dùng gửi lên HĐGSNN xem xét thủ công. Đây là quy trình ngoài hệ thống — ReviewAgent không thay thế HĐGSNN.
