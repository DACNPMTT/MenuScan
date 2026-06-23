# MenuScan Bruno Collection

Thư mục này chứa Bruno collection dùng để test API MenuScan ở môi trường local.

## Mở Collection Trong Bruno

1. Cài Bruno Desktop từ https://www.usebruno.com/downloads.
2. Mở Bruno.
3. Chọn **Open Collection**.
4. Chọn thư mục `bruno/` trong repo này.
5. Chọn environment `Local`.

## Chạy API Local

Chạy từ thư mục gốc của repo:

```bash
make env ENV=local
make deps ENV=local
make backend ENV=local
```

Sau khi chạy xong, API local sẽ ở địa chỉ `http://localhost:8000`.

Trên Windows, thành viên team cũng có thể dùng script PowerShell có sẵn:

```powershell
.\run.ps1 start
.\run.ps1 status
```

Nếu PowerShell chặn script vì Execution Policy, chạy bằng lệnh này:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1 start
```

Dùng `.\run.ps1 stop` khi muốn dừng backend/frontend local.

## Hướng Dẫn Nhanh Cho Thành Viên Team

1. Pull code mới nhất.
2. Cài Bruno Desktop từ https://www.usebruno.com/downloads.
3. Chạy API bằng `make backend ENV=local` hoặc `.\run.ps1 start`.
4. Mở thư mục `bruno/` trong Bruno.
5. Chọn environment `Local`.
6. Test các request trong folder `Live Smoke` trước.

Nếu request `Ready` fail nhưng `Health` pass, nghĩa là API đã chạy nhưng PostgreSQL chưa sẵn sàng. Hãy chạy `make deps ENV=local` hoặc restart bằng `.\run.ps1 restart`.

## Những Request Hiện Tại Nên Pass

Dùng folder `Live Smoke` để test phần backend hiện đã implement:

- `Root`: `GET /`
- `Health`: `GET /health`, kỳ vọng `200` với `{ "status": "ok" }`
- `Ready`: `GET /ready`, kỳ vọng `200` khi PostgreSQL đã sẵn sàng
- `Missing - Not Found`: `GET /missing`, kỳ vọng error wrapper chuẩn với code `NOT_FOUND`

`Ready` có thể trả `503 DEPENDENCY_UNAVAILABLE` nếu container database chưa chạy hoặc dependency/migration chưa sẵn sàng.

## Các Request Theo MVP Contract

Folder `MVP Contract` bám theo tài liệu `doc/content/api-endpoints.md`.
Một số request trong folder này có thể fail cho đến khi backend implement route tương ứng.

Các biến environment dùng trong Bruno:

- `access_token`: dán access token trả về từ flow verify magic link sau khi auth được implement.
- `magic_link_token`: dán raw magic link token để test request `Verify Magic Link`.
- `scan_id`: dán scan UUID trả về từ request `Create Scan`.
- `menu_id`: dán menu UUID trả về từ request `Get Scan Result`.

Với request `Create Scan`, chọn file local cho field multipart `file` trong Bruno trước khi gửi request.

## Test Nhanh API Không Cần Bruno

Dùng các lệnh sau nếu muốn kiểm tra nhanh API trước khi mở Bruno:

```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

Để kiểm tra error wrapper `404`:

```powershell
try {
  Invoke-RestMethod http://localhost:8000/missing
} catch {
  $_.ErrorDetails.Message
}
```
