# Software Requirements Specification - MenuScan

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](./mvp-contract.md)

## 1. Mục tiêu

MenuScan là **trợ lý chọn món cá nhân hoá** cho khách du lịch và người kỹ tính
trong ăn uống: quét menu tiếng lạ / nhiều món không quen và nhận về, cho từng
món, bản dịch + giải thích + phán đoán *hợp/không hợp với bạn và vì sao*, đối
chiếu với hồ sơ khẩu vị của chính người dùng. Nền tảng kỹ thuật là pipeline
OCR + LLM chuyển ảnh menu thành dữ liệu món ăn có cấu trúc — cùng lõi tạo ra
phần gợi ý cá nhân hoá. Sản phẩm là **trợ lý tham khảo, không bảo hành an toàn**.

Người dùng có thể scan ngay với tư cách guest hoặc đăng nhập bằng Magic
Link/email+mật khẩu để có lịch sử; sau đó theo dõi xử lý, xem file gốc cạnh
kết quả OCR/phân tích/dịch, chỉnh sửa kết quả, và chọn món để tính/chia hóa đơn.

## 2. Đối tượng sử dụng

- **Khách du lịch / người kỹ tính ăn uống** cần hiểu menu tiếng lạ và biết món
  nào hợp với mình (dị ứng, chế độ ăn, sở thích) — nhóm người dùng chính.
- Khách nước ngoài cần hiểu menu tiếng Việt khi ăn uống tại Việt Nam.
- Người dùng cần số hóa menu từ ảnh hoặc PDF.
- Thành viên dự án triển khai frontend, backend, OCR, database và QA.

## 3. Phạm vi

### 3.1 In scope

- Magic Link, đăng nhập email+mật khẩu, đặt mật khẩu và quản lý phiên bằng access/refresh token.
- Chỉnh sửa profile (tên hiển thị, ngôn ngữ ưu tiên, dị ứng, chế độ ăn).
- Dashboard entry cho user đã đăng nhập.
- Upload một hoặc nhiều file JPG, JPEG, PNG, WEBP hoặc PDF (hoặc chụp camera); mỗi file tối đa 10 MB, tổng payload tối đa 40 MB.
- Tổng số trang trong một scan tối đa 8.
- OCR, nhận diện ngôn ngữ, phân tích món và dịch sang language tag đích do user chọn.
- Hiển thị file menu gốc cùng dữ liệu có cấu trúc; đổi tiền tệ hiển thị theo tỷ giá.
- Chỉnh sửa kết quả OCR: sửa/thêm/xóa món, xác nhận và lưu menu.
- Tìm kiếm và lọc món theo tên/giá/nhóm.
- Chọn món, thêm phí/thuế/giảm giá, chia bill theo số người.

**Định hướng mới — sẽ triển khai (chưa có trong code, xem
[personalization-tasklist.md](./personalization-tasklist.md)):**

- Hồ sơ khẩu vị mở rộng: sở thích + món ghét chọn từ danh sách cố định.
- Suy luận nguyên liệu/vị mỗi món để đối chiếu với hồ sơ.
- Gợi ý + xếp hạng món theo hồ sơ (nhãn "Gợi ý cho bạn"), giữ cảnh báo dị ứng.
- Khung chat hỏi trợ lý trong màn chi tiết món.
- Luồng nhóm: tạo nhóm, chia sẻ QR, thành viên điền khẩu vị không cần đăng nhập,
  chia bill theo số người trong nhóm.

### 3.2 Out of scope

- Quên hoặc reset mật khẩu (chỉ có đặt mật khẩu sau khi đã đăng nhập).
- Social login.
- Dashboard analytics nâng cao.
- Thanh toán online hoặc gửi đơn đến nhà hàng.
- Tìm kiếm hoặc sinh ảnh riêng cho từng món.

## 4. Yêu cầu chức năng

| ID | Yêu cầu | Mức ưu tiên |
| --- | --- | --- |
| FR-01 | User nhập email để yêu cầu Magic Link. | Must |
| FR-02 | Hệ thống xác minh link một lần và tự tạo user ở lần đầu. | Must |
| FR-03 | Hệ thống cấp access token, rotate refresh token và cho phép logout. | Must |
| FR-04 | Guest hoặc user đã đăng nhập đều tạo được phiên scan; chỉ user đã đăng nhập có lịch sử scan. | Must |
| FR-05 | User upload một hoặc nhiều source file theo quy tắc MVP. | Must |
| FR-06 | Hệ thống lưu file gốc an toàn và tạo phiên scan. | Must |
| FR-07 | Hệ thống OCR, nhận diện ngôn ngữ, phân tích và dịch menu. | Must |
| FR-08 | User theo dõi trạng thái xử lý. | Must |
| FR-09 | Kết quả gồm file gốc, tên món, mô tả, giá, tiền tệ và độ tin cậy khi có. | Must |
| FR-10 | User xác nhận lưu menu. | Must |
| FR-11 | Hệ thống hiển thị lỗi có thể hiểu và cho phép thử lại. | Must |
| FR-12 | Camera capture, chỉnh sửa kết quả OCR, tìm kiếm/lọc món. | Must |
| FR-13 | Tạo bill từ menu, thêm/sửa/xóa items và adjustments, chia bill, chốt hóa đơn. | Must |
| FR-14 | Đổi tiền tệ hiển thị theo tỷ giá thời gian thực. | Must |
| FR-15 | Đăng nhập bằng email+mật khẩu; đặt mật khẩu sau khi đăng nhập. | Must |
| FR-16 | Chỉnh sửa profile: tên hiển thị, ngôn ngữ ưu tiên, dị ứng, chế độ ăn. | Must |

## 5. Yêu cầu phi chức năng

| ID | Yêu cầu |
| --- | --- |
| NFR-01 | Pipeline OCR/LLM có timeout và fallback; Gemini parse mặc định timeout 100 giây. |
| NFR-02 | Giao diện responsive và có trạng thái loading, empty, error rõ ràng. |
| NFR-03 | File gốc và lịch sử chỉ user sở hữu được truy cập. |
| NFR-04 | Magic Link token và refresh token chỉ lưu dạng hash. |
| NFR-05 | Backend xác thực MIME từ nội dung file và không tin extension từ client. |
| NFR-06 | API dùng response/error wrapper thống nhất và có `request_id`. |
| NFR-07 | Mã nguồn chia module Auth, Scan, OCR, Menu, Storage và Shared. |
| NFR-08 | Không trả stack trace, token hoặc thông tin provider trong lỗi. |

## 6. Luồng chính

1. Guest mở Landing Page và chọn Scan Now hoặc đăng nhập.
2. Nếu đăng nhập, guest nhập email và yêu cầu Magic Link, rồi mở link trong 15 phút để hệ thống tạo phiên.
3. User/guest chọn upload menu.
4. Client kiểm tra sơ bộ file; backend kiểm tra lại MIME, kích thước và PDF.
5. Backend lưu file gốc, tạo scan và bắt đầu xử lý bất đồng bộ.
6. Frontend poll trạng thái đến `COMPLETED` hoặc `FAILED`.
7. Khi thành công, frontend hiển thị file gốc cạnh dữ liệu món.
8. User xác nhận lưu menu hoặc scan file khác.

## 7. Luồng lỗi

- Magic Link sai, hết hạn hoặc đã dùng: yêu cầu gửi link mới.
- File sai loại hoặc quá 10 MB: từ chối trước khi tạo scan.
- PDF/tổng scan quá 8 trang hoặc có mật khẩu: từ chối với lỗi validation.
- Không nhận diện được menu: scan chuyển `FAILED` với `OCR_EMPTY_RESULT` hoặc `INVALID_DOCUMENT`.
- OCR/provider tạm lỗi: trả lỗi có thể retry, không làm mất phiên scan.
- Access token hết hạn: frontend gọi refresh một lần rồi retry request.
- Refresh session hết hạn: xóa trạng thái đăng nhập và quay về Magic Link.

## 8. Quy tắc nghiệp vụ

| ID | Quy tắc |
| --- | --- |
| BR-01 | Guest được scan bằng `scan_id`; guest không có danh sách lịch sử theo tài khoản. |
| BR-02 | Magic Link sống 15 phút, dùng một lần; resend cooldown 60 giây. |
| BR-03 | Mỗi scan nhận một hoặc nhiều file; mỗi file tối đa 10 MB, tổng payload tối đa 40 MB. |
| BR-04 | MIME hỗ trợ: JPEG, PNG, WEBP và PDF; tổng scan tối đa 8 trang. |
| BR-05 | Source language tự nhận diện; target language là language tag hợp lệ tối đa 10 ký tự. |
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
