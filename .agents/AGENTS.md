# MenuScan Agent Guide

MenuScan chuyển ảnh/PDF menu thành dữ liệu món ăn có cấu trúc qua OCR/AI. Luồng
MVP: Magic Link → upload một file → xử lý bất đồng bộ → xem nguồn + kết quả → lưu.

## Stack và ranh giới

| Layer | Công nghệ / ownership |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8 trong `frontend/`; chỉ gọi public API |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x trong `app/`; modular layered, không DDD mặc định |
| Data | PostgreSQL 16 là source of truth; Redis chỉ cache/coordination và chưa tích hợp |
| File/AI | Private object storage và OCR/AI provider do backend điều phối; hiện là planned integration |
| Tooling | npm; uv + Ruff + pytest; Docker Compose trong `infras/` |

Backend module đi `router -> service -> repository -> model`. Frontend đi
`app/pages -> features -> shared`. Không layer frontend nào truy cập trực tiếp
PostgreSQL, Redis, storage hoặc provider.

## Nguồn sự thật

Khi mâu thuẫn, ưu tiên:

1. Yêu cầu hiện tại của người dùng.
2. `doc/content/mvp-contract.md` cho scope và business rule.
3. Contract chuyên biệt: API docs hoặc database specification.
4. Code, migration và test đang chạy.
5. README, `doc/ai/` và diagram.

`DB/schema.sql` là schema Sprint 0 cũ, không phải schema MVP. Nguồn database
chuẩn là `doc/content/specification/database.md` cho tới khi migration hiện hành
thay thế rõ ràng.

## Context loading — chỉ đọc khi cần

Luôn đọc file này và kiểm tra `git status`. Không nạp toàn bộ `.agents/rules/`
hoặc `doc/`. Với task code, đọc thêm `.agents/rules/00-core.md` và
`.agents/rules/05-code-conventions.md`.

| Task chạm tới | Đọc thêm | Contract/context tùy nhu cầu |
| --- | --- | --- |
| React, TypeScript, UI | `.agents/rules/10-frontend-react.md` | `doc/ai/architecture.md` cho boundary; `doc/design/` cho UI cụ thể |
| Python, FastAPI, worker, OCR | `.agents/rules/20-backend-python.md` | Section liên quan trong `doc/content/api-endpoints.md`; architecture context cho module/flow |
| PostgreSQL, migration, Redis | `.agents/rules/30-data-postgres-redis.md` | `doc/content/specification/database.md`; database context cho ownership/transaction |
| API, auth, upload, security | `.agents/rules/40-api-security.md` | Section liên quan trong MVP/API docs; response shape ở `doc/content/specification/api-response-template.md` |
| Test, CI, docs | `.agents/rules/50-testing-docs.md` | `doc/content/TestCases_API.md` hoặc tài liệu trực tiếp bị ảnh hưởng |
| Docker/infrastructure | Core + backend/data rule liên quan | `docker-compose.yml` (root), `infras/.env.example`, Dockerfile liên quan |

Chỉ đọc `doc/ai/architecture.md` khi task ảnh hưởng cấu trúc, dependency, module,
cross-layer flow hoặc external integration. Chỉ đọc `doc/ai/database.md` khi task
ảnh hưởng model/table/repository/transaction/ownership/migration/cache. Hai file
này bổ sung context, không thay thế contract.

Tìm heading/từ khóa bằng `rg` trước khi mở tài liệu dài. Diagram `.drawio` chỉ
đọc khi code + contract + context Markdown chưa đủ.

## Hard constraints

- Bám MVP; không tự thêm feature, dependency, abstraction, endpoint hoặc table.
- Backend không tự áp dụng DDD/Clean Architecture/CQRS; giữ module phẳng và chỉ
  tách file/package khi có responsibility thực tế.
- Không giả định Redis, queue, storage hay OCR provider đã sẵn sàng; tích hợp mới
  cần config, health/readiness, failure behavior và test.
- Không hard-code/log secret, token, cookie, PII, raw OCR hoặc production data.
- API/schema dùng chung đổi thì cập nhật consumer, validation, migration, test và
  docs liên quan trong cùng task.
- PostgreSQL là source of truth; frontend chỉ dùng public backend API; backend
  luôn scope authorization/ownership trong query.
- Giữ thay đổi của người dùng; không revert/format file ngoài phạm vi.
- Không tuyên bố hoàn tất nếu chưa chạy kiểm tra phù hợp hoặc chưa nêu rõ lý do.

## Definition of done

Patch đúng scope; implementation, type/contract, migration, test và docs liên
quan đồng bộ. Review diff để loại secret/debug/generated artifact; báo cáo file
chính, kiểm tra đã chạy và rủi ro hoặc việc còn lại.
