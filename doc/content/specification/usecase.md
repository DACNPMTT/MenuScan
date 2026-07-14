# MenuScan MVP Use Cases

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](../mvp-contract.md)

## UC-01 - Đăng nhập bằng Magic Link

**Actor:** Guest

**Tiền điều kiện:** Guest chưa đăng nhập và có thể truy cập email.

**Luồng chính:**

1. Guest nhập email.
2. Hệ thống validate và gửi Magic Link.
3. Guest mở link trong vòng 15 phút.
4. Frontend gửi token đến API verify.
5. Hệ thống dùng token một lần, tạo user nếu cần và tạo session.
6. Frontend xóa token khỏi URL và chuyển user đến Dashboard.

**Ngoại lệ:**

- Email sai định dạng: hiển thị validation.
- Gửi lại trong 60 giây: giữ cooldown.
- Link sai, hết hạn hoặc đã dùng: yêu cầu gửi link mới.
- Email service lỗi: hiển thị lỗi có thể thử lại.

## UC-02 - Scan menu

**Actor:** Guest hoặc user đã đăng nhập

**Tiền điều kiện:** Nếu có session thì session còn hiệu lực; guest có thể scan không cần đăng nhập.

**Luồng chính:**

1. User/guest chọn một hoặc nhiều JPG/JPEG/PNG/WEBP/PDF hợp lệ.
2. Hệ thống kiểm tra mỗi file tối đa 10 MB, tổng payload tối đa 40 MB và tổng scan tối đa 8 trang.
3. Backend lưu file gốc, tạo scan và bắt đầu xử lý.
4. Frontend theo dõi trạng thái.
5. Backend OCR, nhận diện ngôn ngữ, phân tích và dịch.
6. Frontend hiển thị file gốc cạnh danh sách món có cấu trúc.
7. User xác nhận lưu menu.

**Ngoại lệ:**

- File sai loại/quá lớn: từ chối trước xử lý.
- Không đọc được menu: scan chuyển `FAILED`.
- Provider tạm lỗi: hiển thị retry.

## UC-03 - Làm mới phiên

**Actor:** User đã đăng nhập

1. Access token hết hạn.
2. Frontend gọi refresh bằng cookie HttpOnly.
3. Backend rotate refresh token và trả access token mới.
4. Frontend retry request ban đầu đúng một lần.
5. Nếu session hết hạn hoặc bị thu hồi, frontend đăng xuất user.

## UC-04 - Đăng nhập bằng mật khẩu

**Actor:** User đã đặt mật khẩu

**Tiền điều kiện:** User đã tạo tài khoản (qua Magic Link) và đã đặt mật khẩu.

**Luồng chính:**

1. User nhập email và mật khẩu.
2. Hệ thống xác thực thông tin và tạo session.
3. Frontend nhận access token và chuyển đến Dashboard.

**Ngoại lệ:**

- Email/mật khẩu sai hoặc user chưa đặt mật khẩu: trả lỗi xác thực chung.

## UC-05 - Chỉnh sửa kết quả scan

**Actor:** User đã đăng nhập

**Tiền điều kiện:** Scan đã `COMPLETED` và menu đã được tạo.

**Luồng chính:**

1. User xem chi tiết menu từ kết quả scan.
2. User sửa tên/mô tả/giá của món, hoặc thêm/xóa món.
3. User xác nhận lưu menu (`PATCH /menus/{id}` với `is_saved: true`) hoặc
   chốt bản review cuối (`POST /menus/{id}/confirm`).

**Ngoại lệ:**

- Dữ liệu không hợp lệ: hiển thị validation error.

## UC-06 - Tính tiền và chia bill

**Actor:** User đã đăng nhập

**Tiền điều kiện:** Menu đã được tạo từ scan.

**Luồng chính:**

1. User tạo bill mới gắn với menu (`POST /bills`).
2. User chọn món và số lượng (`PATCH /bills/{id}/items`).
3. User thêm phí/thuế/giảm giá nếu cần (`POST /bills/{id}/adjustments`).
4. User chia bill theo số người (`POST /bills/{id}/split`).
5. User chốt hóa đơn (`POST /bills/{id}/finalize`).

**Ngoại lệ:**

- Bill rỗng: không cho phép finalize.
- Tiền tệ không khớp: từ chối thêm item.
- Bill đã finalize: từ chối mọi thay đổi.

## UC-07 - Đổi tiền tệ hiển thị

**Actor:** Guest hoặc user đã đăng nhập

**Tiền điều kiện:** Menu có dữ liệu giá.

**Luồng chính:**

1. User chọn tiền tệ muốn hiển thị.
2. Frontend gọi `GET /exchange-rates?base=<CUR>` lấy tỷ giá.
3. Frontend quy đổi giá hiển thị trên giao diện; dữ liệu gốc trong DB không đổi.

**Ngoại lệ:**

- Tỷ giá không lấy được: hiển thị giá theo tiền gốc.

## UC-08 - Quản lý hồ sơ ăn uống

**Actor:** User đã đăng nhập

**Tiền điều kiện:** User có session hợp lệ.

**Luồng chính:**

1. User mở trang Profile và tạo hồ sơ ăn uống (`POST /auth/me/food-profiles`).
2. User khai preference: dị ứng, món không ăn, khẩu vị ưa thích, quy tắc ăn kiêng —
   mỗi mục gồm `code`, `category`, `preference_type`, `intensity`, `importance`.
3. Hồ sơ đầu tiên tự động được đặt `is_default = true`.
4. User sửa (`PATCH`) hoặc xóa (`DELETE`) hồ sơ khi cần.

**Ngoại lệ:**

- Gửi `preferences` khi update: backend thay thế **toàn bộ** danh sách preference cũ.
- Xóa hồ sơ đang là default: backend chọn hồ sơ còn lại đầu tiên làm default; nếu
  không còn hồ sơ nào, `users.allergies` và `users.dietary_preferences` được reset.

## UC-09 - Làm giàu menu và sinh gợi ý món

**Actor:** User đã đăng nhập

**Tiền điều kiện:** Menu đã tồn tại từ một scan `COMPLETED`.

**Luồng chính:**

1. User mở một menu đã lưu.
2. Frontend gọi `POST /menus/{id}/enrich`.
3. Backend chạy lượt LLM thứ hai: sinh food tag, nguyên liệu chính, mức vị
   (cay/ngọt/mặn/chua/béo/dầu mỡ) và cảnh báo rủi ro cho từng món.
4. Backend chấm verdict cho từng món dựa trên preference đang có, ghi vào
   `food_item_recommendations`.
5. Frontend hiển thị verdict kèm lý do phù hợp / lý do nên tránh.

Bước enrich **cố tình tách khỏi luồng scan** — giữ nó ngoài đường scan chính là
lý do scan nhanh.

**Ngoại lệ:**

- Gọi lại trên menu đã enrich: idempotent, chỉ xử lý các món còn `pending`.
- LLM lỗi: response báo `status` và số món thực sự enrich được, không báo thành
  công giả.
- Vượt throttle: `429 RATE_LIMITED`.

## UC-10 - Tạo phiên ăn nhóm và mời người tham gia

**Actor:** Host (user đã đăng nhập)

**Tiền điều kiện:** Host có session hợp lệ.

**Luồng chính:**

1. Host tạo phiên (`POST /dining/sessions`) với `mode = GROUP`.
2. Backend tạo phiên ở trạng thái `COLLECTING` và sinh invite token.
3. Backend trả `invite_token` **đúng một lần**; database chỉ lưu hash của token.
4. Host chia link mời cho những người cùng bàn.
5. Host theo dõi danh sách người đã tham gia (`GET /dining/sessions/{id}`).
6. Khi mọi người đã khai khẩu vị, host scan menu; gợi ý được chấm trên tập
   preference của **tất cả** participant.
7. Host có thể gỡ một người khỏi bàn — gợi ý sẽ được chấm lại trên tập còn lại.

**Ngoại lệ:**

- Link mời hết hạn (mặc định 12 giờ, tối đa 168 giờ): người mới không vào được.
- Host xóa phiên: soft-delete.

## UC-11 - Tham gia phiên ăn bằng link mời

**Actor:** Participant (**không cần tài khoản**)

**Tiền điều kiện:** Có link mời còn hiệu lực.

**Luồng chính:**

1. Participant mở link mời chứa `invite_token`.
2. Frontend gọi `GET /dining/public/sessions?invite_token=...` xem thông tin phiên.
3. Participant nhập tên hiển thị và khai khẩu vị/dị ứng của mình.
4. Frontend gọi `POST /dining/public/sessions/join?invite_token=...`.
5. Backend tạo participant kèm snapshot preference.

Hai endpoint `public/*` **không yêu cầu đăng nhập** — đây chính là điểm để khách
du lịch được mời vào bàn mà không phải tạo tài khoản.

**Ngoại lệ:**

- Token sai: `404 INVITE_NOT_FOUND`.
- Token hết hạn hoặc hết lượt dùng: `410 INVITE_EXPIRED`.

## UC-12 - Hỏi trợ lý về menu

**Actor:** User đã đăng nhập

**Tiền điều kiện:** Menu đã scan xong.

**Luồng chính:**

1. User đặt câu hỏi về menu (ví dụ "món nào không có đậu phộng?").
2. Frontend gửi `POST /advisor/chat` kèm `menu_id`, câu hỏi, lịch sử hội thoại và
   danh sách món đang quan tâm (`focus_dishes`).
3. Backend grounding câu trả lời trên danh sách món của chính menu đó cộng hồ sơ
   ăn uống của user.
4. Frontend hiển thị câu trả lời.

Lịch sử hội thoại do **client giữ** và gửi kèm mỗi lượt; server **không lưu** tin
nhắn nào.

**Ngoại lệ:**

- Vượt throttle: `429 RATE_LIMITED`.
- Provider lỗi: `503`, và cooldown được **hoàn lại** — user không bị phạt cho một
  lượt họ chưa dùng được.

## UC-13 - Quản lý menu đã lưu

**Actor:** User đã đăng nhập

**Tiền điều kiện:** User có ít nhất một menu đã lưu.

**Luồng chính:**

1. User xem danh sách menu đã lưu (`GET /menus`).
2. User mở một menu (`GET /menus/{id}`).
3. User lọc/tìm món **trong menu đó** (`GET /menus/{id}/items?search=...`).
4. User xóa menu không cần nữa (`DELETE /menus/{id}`) — soft-delete cả menu và
   phiên scan liên quan.

Lưu ý: hệ thống **không có tìm kiếm toàn cục**. `search` chỉ lọc món bên trong
một menu.

**Ngoại lệ:**

- Menu không thuộc user: `403 FORBIDDEN` / `404 MENU_NOT_FOUND`.
