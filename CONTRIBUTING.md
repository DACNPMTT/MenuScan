# Contributing to MenuScan

## Bắt đầu (1 phút)

**Cần cài:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/DACNPMTT/MenuScan.git
cd MenuScan
docker compose up --build
```

| Service  | URL                            |
| -------- | ------------------------------ |
| Frontend | http://localhost:5173          |
| Backend  | http://localhost:8000          |
| Health   | http://localhost:8000/health   |
| Database | localhost:54320 (pgAdmin/DBeaver, user: `menuscan`, password: `localdev`) |

Không cần tạo `.env`. Không cần cài Python hay Node.

---

## Làm việc hàng ngày

### Dev commands

Dùng `dev.ps1` thay vì gõ docker compose:

```powershell
.\dev.ps1 up         # Start services (build + attach logs)
.\dev.ps1 down       # Stop services
.\dev.ps1 restart    # Rebuild + restart
.\dev.ps1 reset      # Xoá DB + rebuild từ đầu
.\dev.ps1 logs       # Xem logs tất cả services
.\dev.ps1 test       # Chạy backend tests (pytest)
.\dev.ps1 lint       # Lint backend (ruff) + frontend (eslint)
.\dev.ps1 shell-be   # Vào shell backend container
.\dev.ps1 shell-fe   # Vào shell frontend container
.\dev.ps1 shell-db   # Mở psql console
.\dev.ps1 status     # Xem trạng thái containers
.\dev.ps1            # Xem tất cả commands
```

### Quy trình code

```
1. Tạo branch từ dev      git checkout dev && git pull && git checkout -b feature/ten-feature
2. Code + test             .\dev.ps1 test && .\dev.ps1 lint
3. Commit                  git add . && git commit -m "feat: mô tả ngắn"
4. Push + tạo PR           git push origin feature/ten-feature → PR vào dev
5. CI chạy tự động         Lint → Test → Build (phải pass hết)
6. Review + merge          Team review, approve, merge
```

### Commit message

Dùng [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: thêm upload menu image
fix: sửa lỗi validate file size
chore: cập nhật dependencies
docs: bổ sung API documentation
refactor: tách service layer cho scan module
test: thêm test cho repository layer
```

---

## Cấu trúc project

```
MenuScan/
├── app/                    # Backend — Python, FastAPI, SQLAlchemy
│   ├── src/
│   │   ├── core/           #   config, database, security
│   │   ├── modules/        #   identity, menu_scan, menu
│   │   └── shared/         #   utilities dùng chung
│   ├── tests/
│   ├── main.py
│   └── Dockerfile.dev
│
├── frontend/               # Frontend — React 19, TypeScript, Vite 8
│   ├── src/
│   │   ├── app/            #   providers, routes
│   │   ├── features/       #   feature modules
│   │   ├── pages/          #   page components
│   │   └── shared/         #   shared components, hooks, lib
│   └── Dockerfile.dev
│
├── doc/                    # Documentation
├── infras/                 # Infrastructure references (deprecated compose)
├── docker-compose.yml      # Dev environment (source of truth)
├── dev.ps1                 # Task runner
└── .env.local.example      # Secret template (khi cần)
```

**Backend:** `router → service → repository → model`. Không import nội bộ giữa modules.

**Frontend:** `pages → features → shared`. Không gọi DB/storage trực tiếp.

---

## Hot-reload chậm trên Windows?

Docker volume mount trên Windows có thể delay hot-reload. Fix:

1. Bật **WSL2** trong Docker Desktop → Settings → General → Use WSL 2 based engine
2. Clone repo **trong WSL** (không phải `/mnt/d/`):
   ```bash
   # Trong WSL terminal:
   cd ~
   git clone https://github.com/DACNPMTT/MenuScan.git
   cd MenuScan
   code .          # VS Code tự mở qua Remote - WSL
   docker compose up --build
   ```

---

## Debug native (không dùng Docker)

Khi cần breakpoint hoặc profiler, chạy backend/frontend ngoài Docker:

```bash
# DB vẫn dùng Docker
docker compose up db -d

# Backend (terminal 1)
cd app
uv sync
$env:DATABASE_URL = "postgresql://menuscan:localdev@localhost:54320/menuscan"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Cần cài thêm: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 22+.

---

## Secrets (khi nào cần)

Hiện tại chưa có secret nào. Khi project integrate OCR/email:

1. Copy template: `cp .env.local.example .env.local`
2. Điền API keys vào `.env.local`
3. `.env.local` đã gitignored — không bao giờ commit lên repo

Lấy key ở đâu → hỏi team lead hoặc xem shared password manager.

---

## CI/CD

**CI** tự chạy khi push/PR vào `dev`:

```
Lint (gate) ──pass──→ Test Backend (có PostgreSQL)
                   ──→ Build Frontend
```

- Chỉ trigger khi đổi `app/`, `frontend/`, hoặc `DB/`
- Lint fail → test/build không chạy
- Phải pass hết mới merge được

**CD** sẽ setup khi MVP sẵn sàng deploy.

---

## Troubleshooting

| Vấn đề | Giải pháp |
| --- | --- |
| Port 54320 đã dùng | Đổi port trong `docker-compose.yml` hoặc tắt PG local |
| Container không start | `.\dev.ps1 reset` (xoá sạch + rebuild) |
| Permission denied `dev.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `npm ci` fail trong container | Xoá volume: `docker compose down -v` rồi `up --build` |
| Backend crash loop | `.\dev.ps1 logs-be` để xem lỗi |
