# MenuScan Architecture Context

> Chỉ đọc khi task ảnh hưởng module, dependency, cross-layer flow hoặc external
> integration. Business/API source of truth: `doc/content/mvp-contract.md` và
> `doc/content/api-endpoints.md`. Đây là kiến trúc đích; planned component không
> được coi là đã triển khai.

## System map

```text
React/Vite -- HTTPS /api/v1 --> FastAPI modular monolith
                                    |-- PostgreSQL 16   source of truth (kể cả throttle)
                                    |-- Object Storage  private source files (local hoặc S3/GCS)
                                    |-- Google Vision   OCR provider
                                    |-- Gemini          parser, translation, enrichment, chat
                                    |-- SMTP/Email      magic link
                                    `-- Exchange API    tỷ giá (cache trong tiến trình)
```

Hiện repository có React/FastAPI app, PostgreSQL Compose, object-storage adapter,
OCR provider wiring (`fake`, `google_vision`), parser wiring (`rule_based`,
`gemini`) và scan pipeline chạy bằng FastAPI background task.

**Redis không phải dependency runtime.** `docker-compose.yml` có container Redis
nhưng **không dòng code nào dùng nó**. Anti-spam throttle chạy bằng một upsert
atomic vào bảng `ai_throttle` trong Postgres (`src/core/rate_limit.py`), cùng cơ
chế với cooldown magic-link. Đừng vẽ Redis vào sơ đồ như một thành phần đang hoạt
động.

**Không có Vector DB / RAG engine.** Không có dependency nào (`pgvector`,
`qdrant`, `pinecone`…) và không có module nào truy vấn embedding. Gợi ý món được
chấm bằng luật trên preference của participant, không phải retrieval.

Background job duy nhất là `run_stale_scan_watchdog` (đăng ký trong lifespan tại
`src/core/application.py`), dùng để `FAILED` các scan kẹt ở `PROCESSING`. Không có
worker queue, không có Celery, không có job phân tích hành vi định kỳ.

Gemini được cấu hình bằng **ba** config tách biệt — `llm` (scan/parser),
`chat_llm` (advisor) và `enrich_llm` (enrichment) — để enrichment không tranh
quota với scan trên cùng một API key.

## Frontend

### Layers and ownership

```text
main.tsx -> app (providers/routes)
            -> pages + layouts
               -> features
                  -> shared
```

| Layer | Sở hữu | Được import |
| --- | --- | --- |
| `app` | bootstrap, providers, route composition/guards | pages, features, layouts, shared |
| `pages` | route-level composition | features, layouts, shared |
| `features/<x>` | business UI, API, hooks, feature types | chính feature, shared |
| `layouts` | reusable page shells | shared |
| `shared` | domain-neutral UI/hook/lib/API foundation | shared only |

Không import ngược lên layer cao hơn, không cycle, không import internal của
feature khác. Cross-feature workflow được compose tại `pages`/`app`; primitive
thật sự trung lập mới chuyển xuống `shared`.

### Feature shape

Chỉ tạo folder cần dùng:

```text
features/<feature>/
  api/          typed request and DTO mapping
  components/   feature-owned UI
  hooks/        reusable feature orchestration
  pages/        feature-owned route screen khi cần
  types.ts
```

- `auth`: Magic Link, verify callback, current user, refresh/logout.
- `menu-scan`: upload, validation, progress polling, terminal state.
- `menu-review`: source preview, structured result, save confirmation.
- `dashboard`: authenticated entry; analytics nâng cao ngoài MVP.
- `billing`: chọn món, tính tiền, chia bill, điều chỉnh phí/thuế/giảm giá.
- `exchange`: đổi tiền tệ hiển thị theo tỷ giá thời gian thực.

State ownership: visual state ở component; reusable feature behavior ở hook;
auth/session ở app provider; shareable filter/page ở URL. API call nằm trong
feature `api/` hoặc `shared/api`, không rải `fetch` trong component. Frontend chỉ
dùng stable API error code và không gọi DB/cache/storage/provider.

Chi tiết triển khai React nằm ở `.agents/rules/10-frontend-react.md`.

## Backend

Backend là modular layered monolith, không phải DDD/Clean Architecture:

```text
HTTP -> router + schemas -> service -> repository -> models/PostgreSQL
                              `------> adapters (storage/email/OCR/Gemini)
```

| Layer | Trách nhiệm | Không được làm |
| --- | --- | --- |
| `router` | auth dependency, validate, gọi service, map HTTP | query DB/provider trực tiếp |
| `schemas` | Pydantic request/response/module DTO | chứa workflow hoặc ORM mapping |
| `service` | business workflow, authorization decision, transaction | phụ thuộc FastAPI Request/Response |
| `repository` | named SQLAlchemy queries, add/flush | business workflow, HTTP/provider call, tự commit tùy ý |
| `models` | table/relationship/constraint | import router/service, gọi provider |
| `adapters` | storage/email/OCR/Gemini client | chứa database workflow hoặc UI concern |
| `core` | config, DB/session, security, logging, rate limit | business logic của module cụ thể |

### Module ownership

Bảy module, wire trong `src/router.py` dưới prefix `/api/v1`:

| Module | Trách nhiệm | Tables |
| --- | --- | --- |
| `identity` | user, Magic Link, mật khẩu, refresh session, food profile | `users`, `magic_link_tokens`, `user_sessions`, `food_profiles`, `food_profile_preferences` |
| `menu_scan` | upload, scan lifecycle, OCR orchestration, watchdog | `scan_sessions`, `scan_source_files`, `ocr_results` |
| `menu` | structured menu, food item, save state, enrichment | `menus`, `food_items` |
| `billing` | bill lifecycle, items, adjustments, split | `bills`, `bill_items`, `bill_adjustments` |
| `dining` | phiên ăn nhóm, invite, participant, recommendation | `dining_sessions`, `dining_session_invites`, `dining_session_participants`, `dining_session_participant_preferences`, `food_item_recommendations`, `food_item_recommendation_participant_breakdowns` |
| `advisor` | chat hỏi đáp về menu (grounding, không lưu lịch sử) | không có table riêng |
| `exchange` | exchange rate proxy, in-process cache | không có table riêng |

`ai_throttle` thuộc `core` (`src/core/rate_limit.py`), không thuộc module nghiệp
vụ nào.

### Module shape and dependencies

Module phẳng, chỉ tạo file có responsibility:

```text
modules/<module>/
  router.py  schemas.py  service.py  repository.py  models.py
  dependencies.py  exceptions.py  tasks.py  adapters/   # optional
```

Dependency đi `router -> service -> repository -> models`. FastAPI dependencies
wire request-scoped session/repository/service/client. Không dùng global mutable
state, service locator, generic CRUD repository hoặc interface một-một. Chỉ tách
`services/`/`repositories/` khi file thật sự có nhiều responsibility.

Module A không import model/repository nội bộ của module B. Gọi service công khai
của owner bằng ID/DTO; workflow atomic xuyên module dùng một orchestration service
và cùng DB session. Không thêm event bus/CQRS/broker cho call đồng bộ đơn giản.

Service sở hữu transaction; repository query/add/flush. External I/O không giữ
transaction mở nếu có thể tách pha. Worker truyền ID + idempotency key, load state
mới nhất và dùng conditional transition.

Chi tiết triển khai Python nằm ở `.agents/rules/20-backend-python.md`;
table/repository context ở `doc/ai/database.md`.

## Runtime flows

### Magic Link

```text
React auth -> identity router -> identity service
           -> identity repositories/PostgreSQL
           -> email adapter
```

Verify consume token và tạo session atomically. Chỉ lưu token hash.

### Scan

```text
React -> scan router/service -> validate + private storage
      -> scan_sessions(PENDING) -> background trigger

background pipeline -> PROCESSING/OCR
                    -> OCR service/provider -> ocr_results
                    -> menu validity gate -> parser -> verifier
                    -> translation -> menus + food_items
                    -> COMPLETED | FAILED

React polls status -> authorized source/result
```

Upload và processing là hai pha; terminal state không quay lui. PostgreSQL là
source of truth duy nhất — không có cache tầng ngoài nào được phép giữ business
data. Đổi API payload phải cập nhật backend schema, frontend type, test và docs
trong cùng task.
