# Core Working Rules

Áp dụng cho mọi task tạo, sửa hoặc review code.

## Trước khi sửa

- Xác định acceptance criteria, layer/file bị ảnh hưởng và source of truth.
- Kiểm tra code/config/test hiện hữu; tìm consumer bằng `rg` trước khi đổi shared
  API, type, schema hoặc environment variable.
- Kiểm tra formatter/linter/compiler gần file; không format ngoài phạm vi.

## Trong khi sửa

- Giữ patch nhỏ, đúng scope và theo pattern đang chạy; không dọn code không liên
  quan hoặc tạo abstraction/dependency chưa có nhu cầu.
- Shared contract đổi thì cập nhật producer, consumer, validation, test và docs
  liên quan trong cùng task.
- Giữ dependency direction: frontend → public API; backend → DB/cache/provider.
- Authorization luôn ở backend và scope theo owner; UI chỉ là UX guard.
- Scan chỉ chuyển `PENDING -> PROCESSING -> COMPLETED|FAILED`; terminal không
  quay lui và operation retry phải idempotent/guarded.

## Trước khi hoàn tất

- Chạy kiểm tra nhỏ nhất đủ chứng minh layer đã sửa; không tuyên bố pass nếu chưa
  chạy. Nếu bị chặn, ghi đúng command và nguyên nhân.
- Review diff để tìm secret, debug code, generated artifact, accidental deletion
  và thay đổi ngoài phạm vi.
- Báo cáo ngắn: thay đổi chính, kiểm tra đã chạy, rủi ro/việc còn lại.
