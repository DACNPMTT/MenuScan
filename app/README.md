# MenuScan Backend

Python 3.12+, FastAPI, SQLAlchemy 2.x và PostgreSQL 16. Backend được tổ chức theo
**modular layered monolith**, không dùng DDD/Clean Architecture mặc định.

Nguồn hướng dẫn:

- Kiến trúc và dependency rules: `../doc/ai/architecture.md`.
- Database ownership: `../doc/ai/database.md`.
- API contract: `../doc/content/api-endpoints.md`.
- Business contract: `../doc/content/mvp-contract.md`.

## Module structure

```text
src/
  core/                    config, database, security, logging
  modules/
    identity/              users, Magic Link, sessions
    menu_scan/             upload, scan lifecycle, OCR orchestration
    menu/                  menus, food items, save state
    billing/               reserved; outside current MVP
  shared/                  domain-neutral technical utilities only
```

Một module triển khai theo luồng:

```text
router -> service -> repository -> models -> PostgreSQL
                 `-> adapters for Redis/storage/email/OCR
```

Các file thông dụng:

```text
modules/<module>/
  router.py
  schemas.py
  service.py
  repository.py
  models.py
  dependencies.py          optional wiring
  exceptions.py
  tasks.py                 optional background work
  adapters/                optional external integrations
```

Chỉ tạo file khi có trách nhiệm thực tế. Không tạo `domain/`, `application/`,
`infrastructure/`, generic repository hoặc interface một-một chỉ để hoàn thiện
sơ đồ kiến trúc.

## Adding backend behavior

1. Xác định module sở hữu endpoint và table.
2. Thêm Pydantic request/response trong `schemas.py`.
3. Thêm workflow và transaction trong `service.py`.
4. Thêm query/persistence có tên rõ trong `repository.py`.
5. Thêm/chỉnh SQLAlchemy mapping và migration nếu schema thay đổi.
6. Wire dependency, expose route và cập nhật API docs/frontend type.
7. Viết test cho service, authorization, error contract và persistence boundary.

Module không import model/repository nội bộ của module khác. Workflow xuyên
module phải gọi service công khai của module owner hoặc có orchestration service
rõ ràng.

## Local commands

From the repository root, use `Makefile` as the canonical local task runner.
The root `docker-compose.yml` starts only dependency containers such as
Postgres and Redis; the backend runs natively.

```bash
make env ENV=local
make install-be
make deps ENV=local
make migrate ENV=local
make backend ENV=local
```

Common backend tasks:

```bash
make test-be ENV=local
make lint-be
```

For direct backend commands from `app/`, load the same values from
`../env/.env.local` before running `uv` commands:

```bash
uv sync --locked --all-groups
uv run alembic upgrade head
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
uv run ruff check .
uv run pytest --tb=short
```

Alembic migration is the only schema source. Do not call
`Base.metadata.create_all()` during startup; every environment must provide
`DATABASE_URL` before migrations run.

- API: `http://localhost:8000`
- Health: `GET /health`
- Readiness target: `GET /ready`

`/health` only reflects the API process; `/ready` should check dependencies
such as the database.

## Runtime configuration

| Environment variable | Default |
| --- | --- |
| `DATABASE_URL` | PostgreSQL local development URL |
| `APP_ENV` | `development` |
| `LOG_LEVEL` | `INFO` |
| `API_V1_PREFIX` | `/api/v1` |
| `CORS_ORIGINS` | `http://localhost:5173` |

`CORS_ORIGINS` is a comma-separated allowlist. Do not combine wildcard origins
with credentialed CORS requests.
