# Chuẩn hóa API Response Template — MenuScan

Tài liệu này định nghĩa cấu trúc Response Wrapper chuẩn chuyên nghiệp áp dụng cho toàn bộ API của dự án MenuScan.

---

## 1. Cấu trúc Response Wrapper chung

### 1.1. Success Response (Trả về thành công)

```json
{
  "success": true,
  "status_code": 200, // Hoặc 201 Created
  "message": "Thông điệp thành công.",
  "data": {} // Có thể là Object, Array hoặc null
}
```

### 1.2. Error Response (Trả về lỗi)

```json
{
  "success": false,
  "status_code": 400, // 400, 401, 403, 404, 500
  "error": {
    "code": "ERROR_CODE_UPPERCASE",
    "message": "Mô tả lỗi chi tiết cho phía Client hiển thị",
    "details": null // Chi tiết bổ sung (ví dụ: mảng lỗi validation đầu vào)
  }
}
```

---

## 2. Bảng định nghĩa HTTP Status Codes

| Mã HTTP | Trạng thái     | Trường hợp sử dụng trong MenuScan                                                                                     |
| :------ | :------------- | :-------------------------------------------------------------------------------------------------------------------- |
| **200** | OK             | Lấy thông tin thành công (Xem menu, danh sách món ăn, profile cá nhân, kết quả OCR).                                  |
| **201** | Created        | Khởi tạo thành công tài nguyên mới (Đăng ký tài khoản, tạo phiên quét mới, tạo giỏ hàng/đơn hàng).                    |
| **400** | Bad Request    | Dữ liệu gửi lên không đúng định dạng, lỗi validation (Email sai định dạng, thiếu mật khẩu, dữ liệu gửi lên bị trống). |
| **401** | Unauthorized   | Người dùng chưa đăng nhập, token hết hạn, hoặc thông tin đăng nhập (email/password) không chính xác.                  |
| **403** | Forbidden      | Người dùng đã đăng nhập nhưng không có quyền hạn truy cập tài nguyên (ví dụ: User thường truy cập API Admin).         |
| **404** | Not Found      | Tài nguyên truy cập không tồn tại (Không tìm thấy Menu ID, User ID hoặc Scan Session ID).                             |
| **500** | Internal Error | Lỗi hệ thống server (Dịch vụ OCR bên ngoài bị sập, lỗi kết nối cơ sở dữ liệu PostgreSQL).                             |

---

## 3. Ví dụ thực tế tiêu biểu

### 3.1. Xác thực và Phân quyền người dùng (POST `/api/v1/auth/login`)

- **Request Body:**

```json
{
  "email": "an.nguyen@example.com",
  "password": "securepassword123"
}
```

- **Success Response (200 OK):**

```json
{
  "success": true,
  "status_code": 200,
  "message": "Đăng nhập thành công.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "full_name": "Nguyen Van An",
      "email": "an.nguyen@example.com",
      "role": "TRAVELER"
    }
  }
}
```

- **Error Response (401 Unauthorized - Sai tài khoản/mật khẩu):**

```json
{
  "success": false,
  "status_code": 401,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Email hoặc mật khẩu không chính xác.",
    "details": null
  }
}
```

- **Error Response (403 Forbidden - Truy cập API Admin bằng tài khoản thường):**

```json
{
  "success": false,
  "status_code": 403,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Bạn không có quyền truy cập tài nguyên này.",
    "details": null
  }
}
```

### 3.2. Số hóa Menu / Lấy kết quả quét (GET `/api/v1/scans/{id}/result`)

- **Success Response (200 OK):**

```json
{
  "success": true,
  "status_code": 200,
  "message": "Lấy thông tin menu thành công.",
  "data": {
    "menu": {
      "id": "d837618b-c842-4778-b0bb-d1178dcff634",
      "title": "Menu Nhà hàng Hoa Sen",
      "source_language": "en",
      "target_language": "vi"
    },
    "food_items": [
      {
        "id": "a2f20df8-5570-411d-aad6-59308a295f65",
        "original_name": "Beef noodle soup",
        "translated_name": "Phở bò",
        "price": 60000.0,
        "currency": "VND",
        "allergen_warnings": ["soy", "fish_sauce"]
      }
    ]
  }
}
```

- **Error Response (404 Not Found):**

```json
{
  "success": false,
  "status_code": 404,
  "error": {
    "code": "SCAN_SESSION_NOT_FOUND",
    "message": "Không tìm thấy phiên quét tương ứng với ID đã cung cấp.",
    "details": null
  }
}
```
