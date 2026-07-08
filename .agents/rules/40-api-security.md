# API and Security Rules

## Contract

- Base URL public là `/api/v1`; ID là UUID, thời gian ISO 8601 UTC và tiền là
  chuỗi decimal.
- Giữ response/error wrapper và stable error code đúng contract. HTTP status là
  nguồn trạng thái; không lặp `status_code` trong body.
- Thay đổi endpoint/payload phải cập nhật API docs, backend schema, frontend
  type/consumer và acceptance test. Không tạo breaking change âm thầm.

## Auth và authorization

- MVP chỉ dùng Magic Link; không thêm password/social auth ngoài task đã duyệt.
- Email trim + lowercase. Response gửi Magic Link không tiết lộ account tồn tại.
- Chỉ lưu hash Magic Link/refresh token. Magic Link 15 phút, một lần dùng; resend
  cooldown 60 giây. Access token 15 phút; refresh session 30 ngày, rotate mỗi lần
  refresh; token reuse phải revoke session family.
- Refresh token chỉ ở cookie `HttpOnly`, `Secure`, `SameSite=Lax`; không trả trong
  JSON. Mọi resource scan/menu/source phải kiểm tra owner ở server.

## Input, upload và output

- Validate body/query/path bằng schema allowlist. Không ghép input vào SQL, shell,
  provider URL, filesystem path hoặc HTML.
- Upload đúng một file, `>0` và `<=10 MB`; allowlist MIME/extension MVP; PDF tối
  đa 5 trang, không password. Kiểm tra content, giới hạn đọc streaming và không
  tin tên file.
- Filename phải sanitize; object key do server sinh. Source file private, chỉ trả
  qua authenticated endpoint hoặc signed URL sống ngắn.
- Error user-facing an toàn; không lộ stack, query, provider metadata, path nội bộ
  hoặc secret. Gắn request ID để điều tra.

## Secrets và vận hành

- Secret chỉ qua environment/secret manager; `.env.example` chứa placeholder an
  toàn, không commit `.env` thật.
- CORS dùng allowlist; không kết hợp wildcard origin với credentials. Rate-limit
  auth, upload và endpoint tốn tài nguyên.
- Log có cấu trúc và redact Authorization, Cookie, token, email khi không cần,
  OCR raw text và signed URL.
