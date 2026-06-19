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

**Actor:** User đã đăng nhập

**Tiền điều kiện:** Session còn hiệu lực.

**Luồng chính:**

1. User chọn một JPG/JPEG/PNG/WEBP/PDF hợp lệ.
2. Hệ thống kiểm tra file tối đa 10 MB; PDF tối đa 5 trang.
3. Backend lưu file gốc, tạo scan và bắt đầu xử lý.
4. Frontend theo dõi trạng thái.
5. Backend OCR, nhận diện ngôn ngữ, phân tích và dịch.
6. Frontend hiển thị file gốc cạnh danh sách món có cấu trúc.
7. User xác nhận lưu menu.

**Ngoại lệ:**

- Guest gọi scan: trả `401 UNAUTHORIZED`.
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
