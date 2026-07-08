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
