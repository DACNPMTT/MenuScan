# MenuScan MVP Contract

> Trạng thái: Đồng bộ với code hiện tại  
> Phiên bản: 2.0  
> Cập nhật: 2026-07-08
> Phạm vi áp dụng: Sprint 1 và Sprint 2 (đã triển khai: camera, sửa món, billing/chia bill, đổi tiền tệ, chỉnh sửa profile)

Tài liệu này là nguồn sự thật duy nhất cho phạm vi sản phẩm, luồng người dùng,
quy tắc upload, dữ liệu trả về và API của MenuScan. Khi tài liệu khác hoặc
Figma khác với tài liệu này, team phải cập nhật tài liệu/Figma theo contract
này trước khi triển khai.

## 1. Mục tiêu MVP

**Định vị sản phẩm:** MenuScan là **trợ lý chọn món cá nhân hoá** cho khách du
lịch và người kỹ tính trong ăn uống. Quét một menu tiếng lạ / nhiều món không
quen, mỗi món được dịch, giải thích và đối chiếu với hồ sơ khẩu vị của chính
người dùng (dị ứng, chế độ ăn, sở thích, món ghét) để cho biết món có hợp không,
vì sao, và cần lưu ý gì. Điểm khác biệt so với app dịch: trả về **phán đoán cá
nhân hoá**, không chỉ dịch chữ. Sản phẩm là **trợ lý tham khảo, KHÔNG bảo hành
an toàn** — cảnh báo dị ứng do AI suy ra, luôn khuyến nghị xác nhận với nhà hàng.

MenuScan cho phép người dùng đăng nhập (Magic Link hoặc email + mật khẩu), tải
menu lên, theo dõi quá trình xử lý OCR, xem đồng thời file gốc với dữ liệu món
ăn có cấu trúc, chỉnh sửa kết quả, và chọn món để tính/chia hóa đơn.

> **Định hướng mới đang triển khai (chưa có trong code):** hồ sơ khẩu vị mở rộng
> (sở thích/món ghét), gợi ý + xếp hạng món theo hồ sơ, khung chat trợ lý, và
> luồng nhóm/QR/chia bill không đăng nhập. Phạm vi và task chi tiết ở
> [personalization-tasklist.md](./personalization-tasklist.md). Các mục dưới đây
> mô tả phần **đã triển khai**; đừng coi phần định hướng mới là đã xong.

Luồng chính:

```text
Đăng nhập (Magic Link hoặc mật khẩu)
  -> Dashboard
  -> Upload menu (hoặc chụp camera)
  -> OCR, nhận diện ngôn ngữ, phân tích và dịch sang ngôn ngữ đích
  -> Xem file menu gốc cùng kết quả có cấu trúc; đổi tiền tệ hiển thị
  -> Chỉnh sửa món, lưu menu
  -> Chọn món -> tính tiền / chia bill / hóa đơn điện tử
```

## 2. Quyết định nghiệp vụ đã chốt

| Nội dung | Quyết định |
| --- | --- |
| Quyền scan | Guest được tạo scan và xem lại scan bằng `scan_id`; chỉ user đã đăng nhập có lịch sử scan/menu theo tài khoản. |
| Tạo tài khoản | Tự động tạo user khi email xác minh Magic Link lần đầu. Không có màn hình đăng ký riêng. |
| Đăng nhập | Magic Link (không mật khẩu) hoặc email + mật khẩu. Mật khẩu được đặt qua `/auth/set-password` sau khi đã đăng nhập; lưu dưới dạng bcrypt hash. |
| File đầu vào | Mỗi phiên scan nhận một hoặc nhiều source file JPG, PNG, WEBP hoặc PDF; trường `file` legacy và `files` đều được hỗ trợ. |
| Dung lượng | Tối đa 10 MB/file, 40 MB/phiên; tổng số trang tối đa 8. |
| Ngôn ngữ nguồn | Hệ thống tự nhận diện. Ưu tiên menu tiếng Việt tại Việt Nam; tiếng Anh khi menu có gloss song ngữ. |
| Ngôn ngữ đích | Language tag chữ thường hợp lệ như `vi`, `en`, `zh`, `pt-br` (tối đa 10 ký tự); mặc định theo ngôn ngữ ưu tiên của user, fallback `vi`. |
| Tiền tệ hiển thị | Giá lưu theo tiền gốc của menu (thường VND). Người dùng có thể đổi tiền tệ hiển thị ở client (quy đổi theo tỷ giá, không ghi đè dữ liệu gốc). |
| Thời gian kỳ vọng | Ảnh một trang kỳ vọng nhanh; pipeline Gemini hiện có timeout mặc định 100 giây và fallback parser/model khi provider timeout hoặc quota lỗi. |
| Ảnh trong kết quả | Hiển thị file menu gốc cạnh dữ liệu trích xuất. MVP không tìm hoặc sinh ảnh riêng cho từng món. |
| Lưu menu | Scan của user xuất hiện trong lịch sử sau khi tạo; `is_saved` đánh dấu menu đã được user xác nhận lưu. Guest không có danh sách lịch sử theo tài khoản. |

## 3. In scope

- Landing Page và điều hướng đến đăng nhập.
- Đăng nhập bằng Magic Link **và** email + mật khẩu; đặt mật khẩu; chỉnh sửa profile (tên hiển thị, ngôn ngữ ưu tiên).
- Access token, refresh token rotation, đăng xuất và lấy user hiện tại.
- Dashboard entry cho người dùng đã đăng nhập.
- Upload một hoặc nhiều ảnh/PDF menu trong một scan, hoặc chụp trực tiếp bằng camera, theo quy tắc đã chốt.
- Lưu và truy cập an toàn file menu gốc.
- OCR, nhận diện ngôn ngữ, phân tích tên món, mô tả, giá và tiền tệ.
- Dịch nội dung menu sang language tag đích hợp lệ mà user chọn.
- Theo dõi trạng thái `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`.
- Hiển thị file menu gốc và danh sách món có cấu trúc; đổi tiền tệ hiển thị theo tỷ giá.
- Chỉnh sửa kết quả OCR: sửa/thêm/xóa món, xác nhận và lưu menu.
- Tìm kiếm và lọc món theo tên/giá/nhóm trên trang menu.
- Chọn món, thêm phí/thuế/giảm giá, chia bill theo số người và xuất hóa đơn điện tử.
- Trạng thái loading, empty và lỗi của luồng chính.
- Discovery feed (Dashboard hero entry) — feed rule-based dựa trên `food_profile`
  + distance; save/skip; Saved tab; "invite friends here" tạo dining session có
  `restaurant_source_id`. Dataset nhà hàng đọc từ `data/restaurants.json`
  (in-memory cache), không lưu database.

## 4. Out of scope

- Quên hoặc reset mật khẩu (chỉ có đặt mật khẩu sau khi đã đăng nhập).
- Guest history theo tài khoản (guest chỉ truy cập lại bằng `scan_id`, không có danh sách lịch sử).
- Đăng nhập Google và các social provider khác.
- Batch nhiều phiên scan độc lập; trong một scan hiện chỉ gom tối đa 8 page/source file.
- Dashboard analytics nâng cao.
- Thanh toán online hoặc gửi đơn đến nhà hàng.
- Tìm ảnh món từ Internet hoặc sinh ảnh món bằng AI.
- Cam kết độ chính xác tuyệt đối của OCR, dịch thuật hoặc cảnh báo dị ứng.

## 5. Auth contract

### 5.1 Quy tắc đăng nhập & session

- Email được trim và chuẩn hóa chữ thường.
- API Magic Link luôn trả thông báo chung để không làm lộ email đã tồn tại hay chưa.
- Magic Link có hiệu lực 15 phút, dùng một lần và bị vô hiệu sau khi xác minh.
- Một email chỉ được yêu cầu gửi lại Magic Link sau 60 giây.
- Yêu cầu Magic Link mới làm vô hiệu các link chưa dùng trước đó của cùng email.
- Đăng nhập bằng mật khẩu: chỉ dùng được sau khi user đã đặt mật khẩu qua
  `/auth/set-password`; mật khẩu lưu dưới dạng bcrypt hash. Sai email/mật khẩu
  hoặc user chưa đặt mật khẩu đều trả lỗi xác thực chung.
- Chỉ lưu hash của token Magic Link và refresh token.
- Lần xác minh Magic Link đầu tiên tự động tạo user ở trạng thái `ACTIVE`.
- Access token (JWT) có hiệu lực 15 phút.
- Refresh token rotate sau mỗi lần refresh, lưu trong cookie `HttpOnly`,
  `Secure` (tắt ở môi trường dev/test). Thuộc tính `SameSite` theo env
  `SESSION_COOKIE_SAMESITE` (default `lax` — an toàn cho same-origin và tự
  chặn CSRF; đặt `none` cho cross-origin production, khi đó CSRF defense
  chuyển sang check `Origin` whitelist ở `/auth/refresh`). Thời hạn session
  theo hằng số `SESSION_TTL` trong code (hiện `30 ngày`); mỗi lần refresh
  gia hạn thêm `SESSION_TTL` (sliding window), chặn bởi absolute cap
  `SESSION_ABSOLUTE_TIMEOUT = 90 ngày` kể từ lúc tạo session.
- Logout xác minh secret của refresh token khớp với session trước khi thu hồi.
- Phát hiện refresh token cũ bị tái sử dụng: trong `REFRESH_GRACE_WINDOW`
  (hiện `30 giây`) sau lần rotate gần nhất, request bị từ chối với
  `SESSION_EXPIRED` và **không** thu hồi session — đây là tín hiệu race từ
  tab khác cùng refresh, không phải replay attack. Ngoài grace window, đây là
  replay thật và session bị thu hồi (`SESSION_REVOKED`).
- User đang ở trạng thái `DISABLED` hoặc đã soft-delete không thể đăng nhập lại
  qua Magic Link — account chỉ mở lại khi admin khôi phục.

### 5.2 Auth endpoints

| Method | Endpoint | Auth | Mục đích |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/magic-links` | Không | Gửi Magic Link đến email. |
| `POST` | `/api/v1/auth/magic-links/verify` | Không | Xác minh token, tạo session và trả access token. |
| `POST` | `/api/v1/auth/login` | Không | Đăng nhập bằng email + mật khẩu, tạo session và trả access token. |
| `POST` | `/api/v1/auth/set-password` | Có | Đặt hoặc đổi mật khẩu cho user hiện tại. |
| `POST` | `/api/v1/auth/refresh` | Refresh cookie | Rotate session và cấp access token mới. |
| `POST` | `/api/v1/auth/logout` | Có | Thu hồi session hiện tại và xóa refresh cookie. |
| `GET` | `/api/v1/auth/me` | Có | Lấy user hiện tại. |
| `PATCH` | `/api/v1/auth/me` | Có | Cập nhật profile (tên hiển thị, ngôn ngữ ưu tiên). |
| `POST` | `/api/v1/auth/me/profile` | Có | Cập nhật profile — bản POST cho client/proxy chặn PATCH. |

Frontend nhận token từ URL callback tại `/auth/verify?token=...`, sau đó gửi
token đến endpoint verify. Token trên URL phải được xóa bằng
`history.replaceState` ngay sau khi đọc.

## 6. Menu Scan contract

### 6.1 Upload rules

| Thuộc tính | Giá trị |
| --- | --- |
| Field | `files` (multi-file) hoặc `file` legacy |
| Số file | `>= 1`, tổng số trang `<= 8` |
| MIME type | `image/jpeg`, `image/png`, `image/webp`, `application/pdf` |
| Extension | `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf` |
| Kích thước | `> 0` và `<= 10 MB` |
| PDF | Tối đa 8 trang trong tổng scan, không nhận file có mật khẩu |
| Target language | Language tag chữ thường hợp lệ, tối đa 10 ký tự (mặc định theo user, fallback `vi`) |

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

Frontend không gọi trực tiếp endpoint nội bộ của OCR provider. Backend chịu
trách nhiệm điều phối upload, OCR, phân tích và dịch.

Xử lý OCR chạy nền (FastAPI background task). Một watchdog định kỳ đánh dấu
`FAILED` các phiên bị kẹt ở `PROCESSING` quá lâu (ví dụ khi tiến trình chết
giữa chừng). Parser LLM có chuỗi dự phòng theo model (mặc định
`gemini-3.1-flash-lite` → `gemini-2.5-flash`) rồi mới về parser theo luật, để một model hết quota không làm
hỏng toàn bộ kết quả.

### 6.3 Menu management endpoints

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/api/v1/menus` | Liệt kê menu đã lưu của user. |
| `GET` | `/api/v1/menus/{menu_id}` | Lấy chi tiết menu. |
| `GET` | `/api/v1/menus/{menu_id}/items` | Liệt kê món (có tìm kiếm/lọc/phân trang). |
| `PATCH` | `/api/v1/menus/{menu_id}` | Xác nhận hoặc bỏ trạng thái lưu menu. |
| `POST` | `/api/v1/menus/{menu_id}/confirm` | Xác nhận bản review cuối của menu. |
| `POST` | `/api/v1/menus/{menu_id}/enrich` | Lượt LLM thứ hai: food tag, mức vị, verdict gợi ý. |
| `POST` | `/api/v1/menus/{menu_id}/items` | Thêm món thủ công. |
| `PATCH` | `/api/v1/menus/{menu_id}/items/{item_id}` | Sửa món. |
| `DELETE` | `/api/v1/menus/{menu_id}/items/{item_id}` | Xóa món. |
| `DELETE` | `/api/v1/menus/{menu_id}` | Xóa menu. |

### 6.4 Billing endpoints

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `POST` | `/api/v1/bills` | Tạo bill nháp (DRAFT) gắn với một menu. |
| `GET` | `/api/v1/bills` | Lịch sử bill của user, mới nhất trước (bản rút gọn). |
| `GET` | `/api/v1/bills/{bill_id}` | Lấy chi tiết bill. |
| `DELETE` | `/api/v1/bills/{bill_id}` | Xóa bill của chính mình. |
| `PATCH` | `/api/v1/bills/{bill_id}/items` | Thay thế danh sách món trên bill theo trạng thái mong muốn. |
| `POST` | `/api/v1/bills/{bill_id}/adjustments` | Thêm phí/thuế/giảm giá. |
| `PATCH` | `/api/v1/bills/{bill_id}/adjustments/{adjustment_id}` | Sửa một khoản điều chỉnh. |
| `DELETE` | `/api/v1/bills/{bill_id}/adjustments/{adjustment_id}` | Xóa một khoản điều chỉnh. |
| `POST` | `/api/v1/bills/{bill_id}/split` | Chia bill theo số người (phân bổ phần lẻ, không mất tiền do làm tròn). |
| `POST` | `/api/v1/bills/{bill_id}/finalize` | Chốt bill (khóa, không sửa được nữa). |

Tiền được truyền bằng chuỗi decimal. Chia bill: mỗi phần được floor và phần dư
được phân bổ cho những người đầu tiên nên tổng các phần bằng đúng `total_amount`.

### 6.5 Dining session endpoints

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `POST` | `/api/v1/dining/sessions` | Tạo phiên ăn kèm invite token. |
| `GET` | `/api/v1/dining/sessions` | Liệt kê phiên do user tạo. |
| `GET` | `/api/v1/dining/sessions/{session_id}` | Chi tiết phiên + participant + preference. |
| `DELETE` | `/api/v1/dining/sessions/{session_id}` | Soft-delete phiên. |
| `DELETE` | `/api/v1/dining/sessions/{session_id}/participants/{participant_id}` | Host gỡ một người khỏi bàn. |
| `GET` | `/api/v1/dining/public/sessions?invite_token=<T>` | **Không cần auth.** Xem nhanh phiên trước khi tham gia. |
| `POST` | `/api/v1/dining/public/sessions/join?invite_token=<T>` | **Không cần auth.** Tham gia phiên và khai khẩu vị. |

Dining session là cách cá nhân hóa gợi ý cho **cả bàn ăn**: host tạo phiên, chia
link mời, từng người khai khẩu vị/dị ứng. Verdict được chấm trên tập preference
của tất cả participant và ghi vào `food_item_recommendations`.

Hai endpoint `public/*` cố tình **không yêu cầu đăng nhập** — khách được mời chỉ
cần `invite_token`, không phải tạo tài khoản. `invite_token` chỉ trả về đúng một
lần lúc tạo phiên; database chỉ lưu hash.

Trạng thái phiên: `COLLECTING` → `SCANNING` → `COMPLETED` / `CLOSED`.

### 6.6 Advisor endpoint

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `POST` | `/api/v1/advisor/chat` | Hỏi đáp về một menu đã scan. |

Auth bắt buộc, có throttle. Câu trả lời được grounding trên danh sách món của
menu đó cộng hồ sơ ăn uống của user. Lịch sử hội thoại do **client giữ** và gửi
kèm mỗi lượt — server **không lưu** tin nhắn nào.

Throttle tính trước khi gọi provider; nếu provider lỗi thì cooldown được hoàn
lại, user không bị phạt cho lượt chưa dùng được.

### 6.7 Tỷ giá / đổi tiền tệ

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| `GET` | `/api/v1/exchange-rates?base=<CUR>` | Trả tỷ giá quy đổi theo `base` (mặc định `VND`). |

Backend proxy nhà cung cấp tỷ giá bên ngoài và cache trong tiến trình theo TTL.
Việc quy đổi là **chỉ để hiển thị** ở client; dữ liệu giá gốc trong DB không đổi.
Khi tỷ giá không lấy được, client hiển thị lại theo tiền gốc.

### 6.8 State machine

```text
PENDING -> PROCESSING -> COMPLETED
                      -> FAILED
```

- `PENDING`: file hợp lệ và phiên đã được tạo.
- `PROCESSING`: OCR/phân tích/dịch đang chạy.
- `COMPLETED`: Pipeline đã tạo menu/result và có thể lấy result; danh sách món có thể rỗng nếu parser không tìm được item chắc chắn.
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
          "allergens": [],
          "dietary_tags": [],
          "confidence_score": 0.94,
          "sort_order": 1
        }
      ]
    }
  },
  "meta": {
    "page": 1,
    "page_size": 6,
    "total": 1,
    "total_pages": 1
  }
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
| `422` | `OCR_EMPTY_RESULT` | OCR không trả về text dùng được. |
| `422` | `INVALID_DOCUMENT` | Text OCR rõ ràng không giống menu. |
| `422` | `TOO_MANY_PAGES` / `INVALID_PDF` | Scan hoặc PDF vượt giới hạn trang / PDF không hợp lệ. |
| `429` | `RATE_LIMITED` | Gửi link hoặc gọi API quá nhanh. |
| `500` | `INTERNAL_ERROR` | Lỗi không dự kiến. |
| `503` | `OCR_PROVIDER_UNAVAILABLE` / `STORAGE_UNAVAILABLE` | OCR hoặc object storage tạm thời không sẵn sàng. |

## 10. Đồng bộ Figma

Các màn hình MVP phải map theo contract:

| Figma | Quy tắc đồng bộ |
| --- | --- |
| Landing | Nút `Login` và `Scan Now` đưa user chưa đăng nhập đến màn hình đăng nhập. |
| Login | Form email Magic Link, kèm tùy chọn đăng nhập bằng mật khẩu; không có forgot/reset password. |
| Pending verification | Dùng cho trạng thái đã gửi email; có resend với cooldown 60 giây. |
| Verification success | Sau khi verify thành công chuyển thẳng đến Dashboard, không quay lại Login. |
| Dashboard | Chỉ user đã đăng nhập truy cập được. |
| Add Menu | Hiển thị đúng định dạng, giới hạn 10 MB/file, 40 MB/phiên và tối đa 8 trang; có chọn ngôn ngữ đích và tùy chọn chụp camera. |
| Processing | Hiển thị state từ API; không giả định thời gian `0.8s`. |
| Scan Results | Hiển thị file gốc từ `source.preview_url` cùng các item; có ô đổi tiền tệ; không dùng ảnh món giả. |
| Menu detail | Sửa/thêm/xóa món, tìm kiếm/lọc, chọn món để tính tiền; ô đổi tiền tệ. |
| Bill / hóa đơn | Chia bill theo số người, thêm phí/thuế/giảm giá, xuất hóa đơn điện tử. |

## 11. Traceability

| Nguồn | Cách sử dụng |
| --- | --- |
| `doc/content/SRS.md` | Yêu cầu sản phẩm rút gọn từ contract này. |
| `doc/content/api-endpoints.md` | Chi tiết request/response của các endpoint đã chốt. |
| `doc/content/specification/database.md` | Mô hình lưu trữ phải hỗ trợ contract; user có `password_hash` (bcrypt), token chỉ lưu hash. |
| `doc/content/specification/api-response-template.md` | Wrapper và error format dùng chung. |
| Figma MenuScan | Nguồn thiết kế giao diện; nghiệp vụ phải tuân theo contract này. |

## 12. Review checklist

- [ ] Product/Team lead xác nhận In scope và Out of scope.
- [ ] Backend xác nhận endpoint, token policy và error codes.
- [ ] Frontend xác nhận callback, polling và dữ liệu kết quả.
- [ ] Database xác nhận user có `password_hash` (bcrypt) và token chỉ lưu hash.
- [ ] QA xác nhận upload matrix, luồng billing/chia bill và acceptance cases.
- [ ] Designer xác nhận màn hình Login (Magic Link + mật khẩu), Menu detail và Bill.
