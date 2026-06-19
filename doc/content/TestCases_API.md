# MenuScan MVP Acceptance Cases

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](./mvp-contract.md)

## Auth

| ID | Trường hợp | Kỳ vọng |
| --- | --- | --- |
| AUTH-01 | Email hợp lệ yêu cầu Magic Link | `202`, response chung, không tiết lộ user tồn tại. |
| AUTH-02 | Email sai định dạng | `400 VALIDATION_ERROR`. |
| AUTH-03 | Resend trước 60 giây | `429 RATE_LIMITED`. |
| AUTH-04 | Token hợp lệ lần đầu | Tạo user/session, trả access token, set refresh cookie. |
| AUTH-05 | Token hợp lệ với user cũ | Tạo session mới, không tạo user trùng. |
| AUTH-06 | Token đã dùng | `400 INVALID_MAGIC_LINK`. |
| AUTH-07 | Token quá 15 phút | `401 MAGIC_LINK_EXPIRED`. |
| AUTH-08 | Refresh hợp lệ | Rotate token, token cũ không dùng lại được. |
| AUTH-09 | Refresh hết hạn/bị thu hồi | `401`, frontend quay về Magic Link. |
| AUTH-10 | Logout | `204`, session bị thu hồi và cookie bị xóa. |

## Upload và scan

| ID | Trường hợp | Kỳ vọng |
| --- | --- | --- |
| SCAN-01 | Guest upload | `401 UNAUTHORIZED`. |
| SCAN-02 | JPG/JPEG/PNG/WEBP hợp lệ <= 10 MB | `202`, tạo đúng một scan. |
| SCAN-03 | PDF hợp lệ <= 10 MB và <= 5 trang | `202`, tạo đúng một scan. |
| SCAN-04 | File rỗng | `400 VALIDATION_ERROR`. |
| SCAN-05 | File > 10 MB | `413 FILE_TOO_LARGE`. |
| SCAN-06 | DOCX/TXT/GIF hoặc MIME giả | `415 UNSUPPORTED_FILE_TYPE`. |
| SCAN-07 | PDF > 5 trang hoặc có mật khẩu | `422 INVALID_PDF`. |
| SCAN-08 | `target_language` ngoài `vi`, `en` | `400 VALIDATION_ERROR`. |
| SCAN-09 | Ảnh không có nội dung menu | Scan `FAILED`, `UNREADABLE_MENU`. |
| SCAN-10 | Scan của user khác | `403 FORBIDDEN`. |
| SCAN-11 | Lấy result khi đang xử lý | `409 SCAN_NOT_READY`. |
| SCAN-12 | OCR thành công | State đi `PENDING -> PROCESSING -> COMPLETED`. |

## Result và lưu menu

| ID | Trường hợp | Kỳ vọng |
| --- | --- | --- |
| RESULT-01 | Result thành công | Có `scan.source.preview_url`, menu và ít nhất một item. |
| RESULT-02 | Mở source ảnh | Trả ảnh đúng MIME và chỉ owner truy cập được. |
| RESULT-03 | Mở source PDF | Trả/redirect PDF đúng MIME và chỉ owner truy cập được. |
| RESULT-04 | Trường OCR không chắc chắn | Trả `null`, không tự tạo dữ liệu giả. |
| RESULT-05 | Giá món | Trả chuỗi decimal và currency khi nhận diện được. |
| RESULT-06 | Lưu menu | `PATCH` cập nhật `is_saved=true`. |
| RESULT-07 | Không có ảnh riêng cho món | UI vẫn hiển thị file menu gốc, không dùng ảnh giả. |

## Error contract

| ID | Trường hợp | Kỳ vọng |
| --- | --- | --- |
| ERR-01 | Validation lỗi | Có `success=false`, `error.code`, `message`, `details`, `request_id`. |
| ERR-02 | Lỗi nội bộ | Không lộ stack trace, token, secret hoặc raw provider error. |
| ERR-03 | Endpoint không tồn tại | Dùng cùng error wrapper. |
