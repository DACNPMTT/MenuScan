# Hướng dẫn làm việc cho thành viên

## 1. Nguyên tắc chung

- Mỗi task trên GitHub Projects tương ứng với một GitHub Issue.
- Mỗi Issue dùng một branch riêng, đặt theo mã task viết thường.
- Ví dụ: task `[S1-08] API Auth - Register + Login` dùng branch `s1-08`.
- Luôn tạo branch mới từ `dev`.
- Không push trực tiếp vào `dev` hoặc `main`.
- Khi hoàn thành task, tạo Pull Request vào `dev` để review.

Repo: `https://github.com/DACNPMTT/MenuScan`

Sprint board: `https://github.com/orgs/DACNPMTT/projects/1`

## 2. Tổng quan dự án

MenuScan là web app gồm ba service:

| Service | Công nghệ | Thư mục | Cổng mặc định |
| :--- | :--- | :--- | :--- |
| Frontend | React, TypeScript, Vite | `frontend/` | `5173` |
| Backend API | Python 3.12, FastAPI | `app/` | `8000` |
| Database | PostgreSQL 16 | Docker volume | `5432` |

Cấu trúc chính:

```text
MenuScan/
├── app/                  # Backend FastAPI
├── frontend/             # Frontend React
├── infras/               # Docker Compose và biến môi trường mẫu
├── doc/                  # Tài liệu dự án
└── README.md
```

## 3. Cài đặt lần đầu

Cần cài đặt:

- Git
- GitHub CLI (`gh`)
- VS Code hoặc IDE phù hợp
- Docker Desktop

Docker Desktop là cách chạy khuyến nghị vì tự dựng đủ frontend, backend và PostgreSQL.

Clone repo và đăng nhập GitHub:

```bash
git clone https://github.com/DACNPMTT/MenuScan.git
cd MenuScan
gh auth login
```

Kiểm tra:

```bash
git --version
gh --version
gh auth status
```

## 4. Cấu hình và chạy dự án

### Cách khuyến nghị: Docker Compose

Từ thư mục gốc `MenuScan`, tạo file cấu hình local:

```bash
cd infras
cp .env.example .env
```

File `infras/.env` đã được Git ignore. Không commit file này.

Khởi động toàn bộ hệ thống:

```bash
docker compose up --build
```

Sau khi khởi động:

| Thành phần | URL |
| :--- | :--- |
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| Health check | `http://localhost:8000/health` |
| PostgreSQL | `localhost:5432` |

Health check hợp lệ:

```json
{"status":"ok"}
```

Dừng hệ thống:

```bash
docker compose down
```

Xem log khi có lỗi:

```bash
docker compose logs -f
```

### Biến môi trường mặc định

File `infras/.env.example` hiện có:

```env
POSTGRES_DB=menuscan
POSTGRES_USER=menuscan
POSTGRES_PASSWORD=menuscan123
DB_PORT=5432
BE_PORT=8000
DATABASE_URL=postgresql://menuscan:menuscan123@db:5432/menuscan
FE_PORT=5173
VITE_API_URL=http://localhost:8000
```

Đây là cấu hình development local. Không dùng mật khẩu mẫu khi deploy production.

### Chạy local khi cần debug

Nếu chỉ cần chạy frontend:

```bash
cd frontend
npm install
npm run dev
```

Nếu chỉ cần chạy backend:

```bash
cd app
uv sync
uv run uvicorn main:app --reload
```

Để chạy local không dùng Docker, máy cần thêm Node.js 20.19+ hoặc 22.12+, npm, Python 3.12+ và `uv`. Nếu backend cần database, vẫn phải chạy PostgreSQL và cấu hình `DATABASE_URL` phù hợp.

## 5. Bắt đầu một task

1. Mở `MenuScan Sprint Board`.
2. Chọn một Issue được giao cho bạn trong cột `Todo`.
3. Đọc kỹ `Mô tả`, `Requirements` và `Ước lượng`.
4. Chuyển Issue sang cột `In Progress`.
5. Chạy block lệnh trong mục `Bắt đầu task` của Issue.

Ví dụ với Issue `#36`, task `[S1-08]`:

```bash
git switch dev
git pull origin dev
gh issue develop 36 --base dev --checkout --name s1-08
```

Lệnh trên sẽ:

- Đồng bộ code mới nhất từ `dev`.
- Tạo branch `s1-08` từ `dev`.
- Liên kết branch với Issue `#36`.
- Checkout sang branch `s1-08`.

Kiểm tra branch hiện tại:

```bash
git branch --show-current
```

## 6. Code và commit

Chỉ sửa code liên quan đến task đang làm. Commit thành từng phần nhỏ:

```bash
git status
git add .
git commit -m "feat(auth): thêm API register"
```

Quy tắc commit:

```text
<loại>(<phạm-vi>): <mô-tả-ngắn>
```

| Loại | Mục đích | Ví dụ |
| :--- | :--- | :--- |
| `feat` | Thêm tính năng | `feat(auth): thêm API login` |
| `fix` | Sửa lỗi | `fix(upload): validate file png` |
| `docs` | Cập nhật tài liệu | `docs(api): thêm ví dụ response` |
| `test` | Thêm hoặc sửa test | `test(auth): thêm case sai password` |
| `refactor` | Cải tiến code, không đổi hành vi | `refactor(ocr): tách parser service` |
| `style` | Chỉnh giao diện | `style(card): chỉnh spacing` |

## 7. Push và tạo Pull Request

Push branch task lên GitHub:

```bash
git push -u origin HEAD
```

Tạo Pull Request vào `dev`:

```bash
gh pr create --base dev --fill
```

Trong nội dung Pull Request, thêm dòng:

```text
Closes #36
```

Thay `36` bằng số Issue đang làm. Khi Pull Request được merge, GitHub sẽ tự động đóng Issue.

Sau khi tạo Pull Request:

1. Chuyển Issue sang cột `Review`.
2. Chờ review.
3. Nếu có comment, sửa code trên cùng branch.
4. Commit và push lại. Pull Request sẽ tự cập nhật.

## 8. Sau khi Pull Request được merge

Không tiếp tục code trên branch cũ. Bắt đầu Issue tiếp theo bằng block lệnh nằm trong Issue mới.

Có thể xóa branch local đã merge:

```bash
git switch dev
git pull origin dev
git branch -d s1-08
```

Thay `s1-08` bằng branch vừa hoàn thành.

## 9. Xử lý conflict

Nếu `git pull origin dev` hoặc merge báo conflict:

```bash
git status
```

Mở file bị conflict, xử lý các đoạn:

```text
[phần code hiện tại]
code hiện tại
[phần code từ nhánh khác]
code từ nhánh khác
[kết thúc đoạn conflict]
```

Sau khi sửa:

```bash
git add .
git commit -m "fix: resolve merge conflict"
git push
```

Nếu không chắc cách xử lý, dừng lại và hỏi người review trước khi push.

## 10. Checklist trước khi tạo Pull Request

- [ ] Đang dùng branch theo mã task, ví dụ `s1-08`.
- [ ] Chỉ sửa file liên quan đến task.
- [ ] Code chạy được trên máy local.
- [ ] Health check backend trả về `{"status":"ok"}` nếu task liên quan backend.
- [ ] Đã chạy test phù hợp.
- [ ] Không commit file cấu hình bí mật như `.env`.
- [ ] Pull Request có `Closes #<issue-number>`.
- [ ] Issue đã được chuyển sang cột `Review`.

## 11. Những điều không nên làm

- Không push trực tiếp vào `main` hoặc `dev`.
- Không dùng branch chung cho nhiều task.
- Không làm nhiều Issue trên cùng một branch.
- Không tự merge Pull Request khi chưa được review.
- Không force push nếu chưa thông báo cho team.
- Không commit token, mật khẩu hoặc file `.env`.
