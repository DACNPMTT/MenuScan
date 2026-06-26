# Software Requirements Specification - MenuScan MVP

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](./mvp-contract.md)

## 1. Mục tiêu

MenuScan giúp người dùng chuyển ảnh hoặc PDF menu thành dữ liệu món ăn có cấu
trúc. Người dùng đăng nhập bằng Magic Link, upload menu, theo dõi xử lý và xem
file gốc cạnh kết quả OCR/phân tích/dịch trước khi xác nhận lưu.

## 2. Đối tượng sử dụng

- Người dùng cần số hóa menu từ ảnh hoặc PDF.
- Khách nước ngoài cần hiểu menu tiếng Việt khi ăn uống tại Việt Nam.
- Thành viên dự án triển khai frontend, backend, OCR, database và QA.

## 3. Phạm vi

### 3.1 In scope

- Magic Link và quản lý phiên bằng access/refresh token.
- Dashboard entry cho user đã đăng nhập.
- Upload một file JPG, JPEG, PNG, WEBP hoặc PDF tối đa 10 MB.
- PDF tối đa 5 trang.
- OCR, nhận diện ngôn ngữ, phân tích món và dịch Việt-Anh.
- Hiển thị file menu gốc cùng dữ liệu có cấu trúc.
- Xác nhận lưu menu.

### 3.2 Out of scope

- Email/password, đăng ký riêng và khôi phục mật khẩu.
- Guest scan.
- Social login.
- Camera, chỉnh sửa OCR, tìm kiếm/lọc và dashboard analytics trong Sprint 1.
- Chọn món, phụ phí, chia bill, hóa đơn điện tử và thanh toán trong Sprint 1.
- Tìm kiếm hoặc sinh ảnh riêng cho từng món.

## 4. Yêu cầu chức năng

| ID | Yêu cầu | Mức ưu tiên |
| --- | --- | --- |
| FR-01 | User nhập email để yêu cầu Magic Link. | Must |
| FR-02 | Hệ thống xác minh link một lần và tự tạo user ở lần đầu. | Must |
| FR-03 | Hệ thống cấp access token, rotate refresh token và cho phép logout. | Must |
| FR-04 | Chỉ user đã đăng nhập được tạo phiên scan. | Must |
| FR-05 | User upload đúng một file theo quy tắc MVP. | Must |
| FR-06 | Hệ thống lưu file gốc an toàn và tạo phiên scan. | Must |
| FR-07 | Hệ thống OCR, nhận diện ngôn ngữ, phân tích và dịch menu. | Must |
| FR-08 | User theo dõi trạng thái xử lý. | Must |
| FR-09 | Kết quả gồm file gốc, tên món, mô tả, giá, tiền tệ và độ tin cậy khi có. | Must |
| FR-10 | User xác nhận lưu menu. | Must |
| FR-11 | Hệ thống hiển thị lỗi có thể hiểu và cho phép thử lại. | Must |
| FR-12 | Camera, chỉnh sửa kết quả, search/filter và bill splitting được mở rộng trong Sprint 2. | Should |

## 5. Yêu cầu phi chức năng

| ID | Yêu cầu |
| --- | --- |
| NFR-01 | Ảnh một trang kỳ vọng hoàn tất trong 30 giây; PDF tối đa 5 trang trong 60 giây khi dịch vụ bình thường. |
| NFR-02 | Giao diện responsive và có trạng thái loading, empty, error rõ ràng. |
| NFR-03 | File gốc và lịch sử chỉ user sở hữu được truy cập. |
| NFR-04 | Magic Link token và refresh token chỉ lưu dạng hash. |
| NFR-05 | Backend xác thực MIME từ nội dung file và không tin extension từ client. |
| NFR-06 | API dùng response/error wrapper thống nhất và có `request_id`. |
| NFR-07 | Mã nguồn chia module Auth, Scan, OCR, Menu, Storage và Shared. |
| NFR-08 | Không trả stack trace, token hoặc thông tin provider trong lỗi. |

## 6. Luồng chính

1. Guest mở Landing Page và chọn Login hoặc Scan Now.
2. Guest nhập email và yêu cầu Magic Link.
3. User mở link trong 15 phút; hệ thống xác minh và tạo phiên.
4. User vào Dashboard và chọn upload menu.
5. Client kiểm tra sơ bộ file; backend kiểm tra lại MIME, kích thước và PDF.
6. Backend lưu file gốc, tạo scan và bắt đầu xử lý bất đồng bộ.
7. Frontend poll trạng thái đến `COMPLETED` hoặc `FAILED`.
8. Khi thành công, frontend hiển thị file gốc cạnh dữ liệu món.
9. User xác nhận lưu menu hoặc scan file khác.

## 7. Luồng lỗi

- Magic Link sai, hết hạn hoặc đã dùng: yêu cầu gửi link mới.
- File sai loại hoặc quá 10 MB: từ chối trước khi tạo scan.
- PDF quá 5 trang hoặc có mật khẩu: từ chối với lỗi validation.
- Không nhận diện được menu: scan chuyển `FAILED` với `UNREADABLE_MENU`.
- OCR/provider tạm lỗi: trả lỗi có thể retry, không làm mất phiên scan.
- Access token hết hạn: frontend gọi refresh một lần rồi retry request.
- Refresh session hết hạn: xóa trạng thái đăng nhập và quay về Magic Link.

## 8. Quy tắc nghiệp vụ

| ID | Quy tắc |
| --- | --- |
| BR-01 | Guest không được scan hoặc xem lịch sử. |
| BR-02 | Magic Link sống 15 phút, dùng một lần; resend cooldown 60 giây. |
| BR-03 | Mỗi scan nhận đúng một file tối đa 10 MB. |
| BR-04 | MIME hỗ trợ: JPEG, PNG, WEBP và PDF; PDF tối đa 5 trang. |
| BR-05 | Source language tự nhận diện; target language chỉ `vi` hoặc `en`. |
| BR-06 | Chỉ `COMPLETED` mới có result; `FAILED` phải có error code. |
| BR-07 | Result phải có đường dẫn truy cập file menu gốc. |
| BR-08 | MVP không tạo hoặc tìm ảnh riêng cho món ăn. |
| BR-09 | Menu chỉ vào lịch sử đã lưu sau khi user xác nhận. |

## 9. Dữ liệu cốt lõi

- `User`: id, email, display_name, preferred_language, role, status, timestamps.
- `MagicLinkToken`: user/email, token_hash, expires_at, consumed_at.
- `UserSession`: user_id, refresh_token_hash, expires_at, revoked_at.
- `ScanSession`: user_id, source metadata, target_language, status, error, timestamps.
- `OcrResult`: raw_text, detected_language, confidence, provider metadata.
- `Menu`: scan_session_id, title, currency, is_saved.
- `FoodItem`: tên gốc/dịch, mô tả, giá, tiền tệ, category, confidence, sort_order.

## 10. Tài liệu liên quan

- API: [api-endpoints.md](./api-endpoints.md)
- Database: [specification/database.md](./specification/database.md)
- Response wrapper: [specification/api-response-template.md](./specification/api-response-template.md)
- Use case: [specification/usecase.md](./specification/usecase.md)
