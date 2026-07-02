# MenuScan MVP Contract

> Trạng thái: Ready for team review  
> Phiên bản: 1.0  
> Cập nhật: 2026-06-20  
> Phạm vi áp dụng: Sprint 1 và các task Sprint 2 sử dụng dữ liệu từ luồng scan

Tài liệu này là nguồn sự thật duy nhất cho phạm vi MVP, luồng người dùng,
quy tắc upload, dữ liệu trả về và API của MenuScan. Khi tài liệu khác hoặc
Figma khác với tài liệu này, team phải cập nhật tài liệu/Figma theo contract
này trước khi triển khai.

## 1. Mục tiêu MVP

MenuScan cho phép người dùng đăng nhập không mật khẩu, tải menu lên, theo dõi
quá trình xử lý OCR và xem đồng thời file gốc với dữ liệu món ăn có cấu trúc.

Luồng chính:

```text
Magic Link
  -> Dashboard
  -> Upload menu
  -> OCR, nhận diện ngôn ngữ, phân tích và dịch
  -> Xem file menu gốc cùng kết quả có cấu trúc
  -> Lưu menu
```

## 2. Quyết định nghiệp vụ đã chốt

| Nội dung | Quyết định |
| --- | --- |
| Quyền scan | Bắt buộc đăng nhập. Guest chỉ xem Landing Page và gửi yêu cầu Magic Link. |
| Tạo tài khoản | Tự động tạo user khi email xác minh Magic Link lần đầu. Không có màn hình đăng ký riêng trong MVP. |
| Đăng nhập | Chỉ dùng Magic Link. Không có mật khẩu, quên mật khẩu hoặc reset mật khẩu. |
| File đầu vào | Mỗi phiên scan nhận đúng một file JPG, PNG, WEBP hoặc PDF. |
| Dung lượng | Tối đa 10 MB/file. PDF tối đa 5 trang. |
| Ngôn ngữ nguồn | Hệ thống tự nhận diện. MVP ưu tiên menu tiếng Việt tại Việt Nam; tiếng Anh chỉ là trường hợp phụ khi menu có gloss song ngữ. |
| Ngôn ngữ đích | `vi` hoặc `en`; mặc định theo ngôn ngữ ưu tiên của user, fallback `en` cho khách nước ngoài. |
| Thời gian kỳ vọng | Ảnh một trang: tối đa 30 giây; PDF tối đa 5 trang: tối đa 60 giây trong điều kiện dịch vụ bình thường. |
| Ảnh trong kết quả | Hiển thị file menu gốc cạnh dữ liệu trích xuất. MVP không tìm hoặc sinh ảnh riêng cho từng món. |
| Lưu menu | Kết quả chỉ vào lịch sử sau khi user xác nhận lưu. File/phiên chưa lưu có thể được dọn theo chính sách lưu trữ. |

## 3. In scope

- Landing Page và điều hướng đến đăng nhập.
- Đăng nhập bằng email Magic Link.
- Access token, refresh token rotation, đăng xuất và lấy user hiện tại.
- Dashboard entry cho người dùng đã đăng nhập.
- Upload một ảnh hoặc PDF menu theo quy tắc đã chốt.
- Lưu và truy cập an toàn file menu gốc.
- OCR, nhận diện ngôn ngữ, phân tích tên món, mô tả, giá và tiền tệ.
- Dịch nội dung menu tiếng Việt sang ngôn ngữ hiển thị của user; MVP hỗ trợ `en` và `vi`.
- Theo dõi trạng thái `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.
- Hiển thị file menu gốc và danh sách món có cấu trúc.
- Xác nhận lưu menu.
- Trạng thái loading, empty và lỗi của luồng chính.

## 4. Out of scope

- Email/password, đăng ký bằng mật khẩu, quên hoặc reset mật khẩu.
- Guest scan hoặc guest history.
- Đăng nhập Google và các social provider khác.
- Chụp camera trực tiếp; triển khai ở Sprint 2.
- Batch upload nhiều file trong một phiên.
- Chỉnh sửa kết quả OCR; triển khai ở Sprint 2.
- Tìm kiếm, lọc, dashboard analytics và lịch sử nâng cao; triển khai ở Sprint 2.
- Chọn món, phí dịch vụ, thuế, giảm giá, chia bill và hóa đơn điện tử; triển khai ở Sprint 2.
- Thanh toán online hoặc gửi đơn đến nhà hàng.
- Tìm ảnh món từ Internet hoặc sinh ảnh món bằng AI.
- Cam kết độ chính xác tuyệt đối của OCR, dịch thuật hoặc cảnh báo dị ứng.

## 5. Auth contract

### 5.1 Quy tắc Magic Link

- Email được trim và chuẩn hóa chữ thường.
- API luôn trả thông báo chung để không làm lộ email đã tồn tại hay chưa.
- Link có hiệu lực 15 phút, dùng một lần và bị vô hiệu sau khi xác minh.
- Một email chỉ được yêu cầu gửi lại sau 60 giây.
- Yêu cầu link mới làm vô hiệu các link chưa dùng trước đó của cùng email.
- Chỉ lưu hash của token Magic Link và refresh token.
- Lần xác minh đầu tiên tự động tạo user ở trạng thái `ACTIVE`.
- Access token có hiệu lực 15 phút.
- Refresh token có hiệu lực 30 ngày, được rotate sau mỗi lần refresh và lưu
  trong cookie `HttpOnly`, `Secure`, `SameSite=Lax`.
- Nếu phát hiện refresh token cũ bị tái sử dụng, toàn bộ session family liên
  quan phải bị thu hồi.

### 5.2 Auth endpoints

| Method | Endpoint | Auth | Mục đích |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/magic-links` | Không | Gửi Magic Link đến email. |
| `POST` | `/api/v1/auth/magic-links/verify` | Không | Xác minh token, tạo session và trả access token. |
| `POST` | `/api/v1/auth/refresh` | Refresh cookie | Rotate session và cấp access token mới. |
| `POST` | `/api/v1/auth/logout` | Có | Thu hồi session hiện tại và xóa refresh cookie. |
| `GET` | `/api/v1/auth/me` | Có | Lấy user hiện tại. |

Frontend nhận token từ URL callback tại `/auth/verify?token=...`, sau đó gửi
token đến endpoint verify. Token trên URL phải được xóa bằng
`history.replaceState` ngay sau khi đọc.

## 6. Menu Scan contract

### 6.1 Upload rules

| Thuộc tính | Giá trị |
| --- | --- |
| Field | `file` |
| Số file | `1` |
| MIME type | `image/jpeg`, `image/png`, `image/webp`, `application/pdf` |
| Extension | `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf` |
| Kích thước | `> 0` và `<= 10 MB` |
| PDF | Tối đa 5 trang, không nhận file có mật khẩu |
| Target language | `vi` hoặc `en` |

Backend phải kiểm tra MIME type từ nội dung file, không chỉ dựa vào tên file.
File không đọc được, ảnh không có chữ hoặc PDF không hợp lệ phải kết thúc phiên
ở trạng thái `FAILED` với mã lỗi phù hợp.

### 6.2 Scan endpoints

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/api/v1/scans` | Liệt kê lịch sử scan của user hiện tại, mới nhất trước. |
| `POST` | `/api/v1/scans` | Upload file, tạo phiên và bắt đầu xử lý bất đồng bộ. |
| `GET` | `/api/v1/scans/{scan_id}` | Lấy trạng thái và tiến trình xử lý. |
| `GET` | `/api/v1/scans/{scan_id}/source` | Trả file gốc hoặc redirect đến URL ký tạm thời. |
| `GET` | `/api/v1/scans/{scan_id}/result` | Trả menu và danh sách món có cấu trúc. |
| `PATCH` | `/api/v1/menus/{menu_id}` | Xác nhận hoặc bỏ trạng thái lưu menu. |

Frontend không gọi trực tiếp endpoint nội bộ của OCR provider. Backend chịu
trách nhiệm điều phối upload, OCR, phân tích và dịch.

### 6.3 State machine

```text
PENDING -> PROCESSING -> COMPLETED
                      -> FAILED
```

- `PENDING`: file hợp lệ và phiên đã được tạo.
- `PROCESSING`: OCR/phân tích/dịch đang chạy.
- `COMPLETED`: đã có ít nhất một món hợp lệ và có thể lấy result.
- `FAILED`: không thể hoàn tất; có `error.code` và thông điệp an toàn cho user.
- Phiên `COMPLETED` hoặc `FAILED` không quay lại trạng thái trước đó.

## 7. Response contract

Mọi API JSON dùng cùng một wrapper.

Success:

```json
{
  "success": true,
  "data": {},
  "meta": null
}
```

Error:

```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File vượt quá dung lượng 10 MB.",
    "details": null,
    "request_id": "req_01J..."
  }
}
```

Quy tắc:

- HTTP status là nguồn trạng thái HTTP; không lặp `status_code` trong body.
- `code` ổn định để frontend xử lý; `message` có thể hiển thị cho user.
- Lỗi validation dùng `details.fields`.
- Không trả stack trace, provider secret hoặc raw exception.

## 8. Dữ liệu kết quả tối thiểu

```json
{
  "success": true,
  "data": {
    "scan": {
      "id": "71151f64-39c7-4419-810a-c0835bafe341",
      "status": "COMPLETED",
      "source": {
        "file_name": "menu.jpg",
        "mime_type": "image/jpeg",
        "file_size": 2458912,
        "preview_url": "/api/v1/scans/71151f64-39c7-4419-810a-c0835bafe341/source"
      },
      "detected_language": "vi",
      "target_language": "en",
      "processing_time_ms": 8200
    },
    "menu": {
      "id": "d837618b-c842-4778-b0bb-d1178dcff634",
      "title": "Menu Nhà hàng Hoa Sen",
      "default_currency": "VND",
      "is_saved": false,
      "items": [
        {
          "id": "a2f20df8-5570-411d-aad6-59308a295f65",
          "original_name": "Phở bò",
          "translated_name": "Beef noodle soup",
          "original_description": null,
          "translated_description": null,
          "price": "60000.00",
          "currency": "VND",
          "category": null,
          "confidence_score": 0.94,
          "sort_order": 1
        }
      ]
    }
  },
  "meta": null
}
```

Tiền được truyền bằng chuỗi decimal để tránh sai số số thực. Trường OCR không
chắc chắn được phép `null`; frontend phải hiển thị trạng thái thiếu dữ liệu thay
vì tự suy đoán.

## 9. Error codes bắt buộc

| HTTP | Code | Trường hợp |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | Body/query không hợp lệ. |
| `400` | `INVALID_MAGIC_LINK` | Magic Link sai hoặc đã dùng. |
| `401` | `UNAUTHORIZED` | Thiếu hoặc sai access token. |
| `401` | `MAGIC_LINK_EXPIRED` | Magic Link hết hạn. |
| `401` | `SESSION_EXPIRED` | Refresh session hết hạn. |
| `403` | `FORBIDDEN` | Tài nguyên không thuộc user. |
| `404` | `SCAN_NOT_FOUND` | Không tìm thấy phiên scan. |
| `409` | `SCAN_NOT_READY` | Result chưa sẵn sàng. |
| `413` | `FILE_TOO_LARGE` | File lớn hơn 10 MB. |
| `415` | `UNSUPPORTED_FILE_TYPE` | MIME type không hỗ trợ. |
| `422` | `UNREADABLE_MENU` | File hợp lệ nhưng không đọc được menu. |
| `429` | `RATE_LIMITED` | Gửi link hoặc gọi API quá nhanh. |
| `500` | `INTERNAL_ERROR` | Lỗi không dự kiến. |
| `503` | `PROCESSING_SERVICE_UNAVAILABLE` | OCR/dịch vụ phụ thuộc tạm thời không sẵn sàng. |

## 10. Đồng bộ Figma

Các màn hình MVP phải map theo contract:

| Figma | Quy tắc đồng bộ |
| --- | --- |
| Landing | Nút `Login` và `Scan Now` đưa user chưa đăng nhập đến màn hình Magic Link. |
| Login/Register cũ | Thay bằng một form email `Send magic link`; bỏ password, sign-up và forgot password. |
| Pending verification | Dùng cho trạng thái đã gửi email; có resend với cooldown 60 giây. |
| Verification success | Sau khi verify thành công chuyển thẳng đến Dashboard, không quay lại Login. |
| Dashboard | Chỉ user đã đăng nhập truy cập được. |
| Add Menu | Hiển thị đúng định dạng, giới hạn 10 MB và PDF tối đa 5 trang. |
| Processing | Hiển thị state từ API; không giả định thời gian `0.8s`. |
| Scan Results | Hiển thị file gốc từ `source.preview_url` cùng các item; không dùng ảnh món giả. |

## 11. Traceability

| Nguồn | Cách sử dụng |
| --- | --- |
| `doc/content/SRS.md` | Yêu cầu sản phẩm rút gọn từ contract này. |
| `doc/content/api-endpoints.md` | Chi tiết request/response của các endpoint đã chốt. |
| `doc/content/specification/database.md` | Mô hình lưu trữ phải hỗ trợ contract, không thêm password user. |
| `doc/content/specification/api-response-template.md` | Wrapper và error format dùng chung. |
| Figma MenuScan | Nguồn thiết kế giao diện; nghiệp vụ phải tuân theo contract này. |

## 12. Review checklist

- [ ] Product/Team lead xác nhận In scope và Out of scope.
- [ ] Backend xác nhận endpoint, token policy và error codes.
- [ ] Frontend xác nhận callback, polling và dữ liệu kết quả.
- [ ] Database xác nhận user không có password và token chỉ lưu hash.
- [ ] QA xác nhận upload matrix và acceptance cases.
- [ ] Designer cập nhật màn hình Login/Register cũ thành Magic Link.
