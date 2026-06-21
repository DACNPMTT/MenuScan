# MenuScan Architecture Context

> Chỉ đọc khi task ảnh hưởng module, dependency, cross-layer flow hoặc external
> integration. Business/API source of truth: `doc/content/mvp-contract.md` và
> `doc/content/api-endpoints.md`. Đây là kiến trúc đích; planned component không
> được coi là đã triển khai.

## System map

```text
React/Vite -- HTTPS /api/v1 --> FastAPI modular monolith
                                    |-- PostgreSQL 16   source of truth
                                    |-- Redis           planned cache/coordination
                                    |-- Object Storage  planned private files
                                    `-- OCR/AI          planned extraction/translation
```

Hiện repository có React/FastAPI scaffold và PostgreSQL Compose. Redis, object
storage, worker/queue và OCR/AI cần code, dependency, config và test trước khi dùng.

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
- `billing`: future scaffold, ngoài MVP cho tới khi contract thay đổi.

State ownership: visual state ở component; reusable feature behavior ở hook;
auth/session ở app provider; shareable filter/page ở URL. API call nằm trong
feature `api/` hoặc `shared/api`, không rải `fetch` trong component. Frontend chỉ
dùng stable API error code và không gọi DB/cache/storage/provider.

Chi tiết triển khai React nằm ở `.agents/rules/10-frontend-react.md`.

## Backend

Backend là modular layered monolith, không phải DDD/Clean Architecture:

```text
HTTP -> router + schemas -> service -> repository -> models/PostgreSQL
                              `------> adapters (Redis/storage/email/OCR)
```

| Layer | Trách nhiệm | Không được làm |
| --- | --- | --- |
| `router` | auth dependency, validate, gọi service, map HTTP | query DB/provider trực tiếp |
| `schemas` | Pydantic request/response/module DTO | chứa workflow hoặc ORM mapping |
| `service` | business workflow, authorization decision, transaction | phụ thuộc FastAPI Request/Response |
| `repository` | named SQLAlchemy queries, add/flush | business workflow, HTTP/provider call, tự commit tùy ý |
| `models` | table/relationship/constraint | import router/service, gọi provider |
| `adapters` | Redis/storage/email/OCR client | chứa database workflow hoặc UI concern |
| `core` | config, DB/session, security, logging | business logic của module cụ thể |

### Module ownership

| Module | Trách nhiệm | Tables |
| --- | --- | --- |
| `identity` | user, Magic Link, refresh session | `users`, `magic_link_tokens`, `user_sessions` |
| `menu_scan` | upload, scan lifecycle, OCR orchestration | `scan_sessions`, `ocr_results` |
| `menu` | structured menu, food item, save state | `menus`, `food_items` |
| `billing` | ngoài MVP | không thêm table/flow khi contract chưa duyệt |

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

worker/service -> PROCESSING -> OCR/AI
               -> ocr_results + menus + food_items
               -> COMPLETED | FAILED

React polls status -> authorized source/result
```

Upload và processing là hai pha; terminal state không quay lui. PostgreSQL là
source of truth, Redis failure không được làm mất business data. Đổi API payload
phải cập nhật backend schema, frontend type, test và docs trong cùng task.
