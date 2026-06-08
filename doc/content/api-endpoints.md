# MenuScan API Endpoints

Tai lieu nay mo ta API contract du kien cho MVP MenuScan. Backend hien tai moi co health check co ban, cac endpoint duoi day la dac ta de frontend, backend va test co cung mot chuan trien khai.

- Base URL: `/api/v1`
- Content type mac dinh: `application/json`
- Auth scheme: `Authorization: Bearer <access_token>`
- Dinh dang thoi gian: ISO 8601 UTC, vi du `2026-06-09T08:30:00Z`
- Dinh dang loi chung:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body is invalid",
    "details": {}
  }
}
```

## Auth Module

### 1. Register

- URL: `/api/v1/auth/register`
- Method: `POST`
- Auth required: No
- Headers:
  - `Content-Type: application/json`
- Request body:

```json
{
  "full_name": "Nguyen Van An",
  "email": "an.nguyen@example.com",
  "password": "Password123!",
  "preferred_language": "vi"
}
```

- Response body:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Nguyen Van An",
  "email": "an.nguyen@example.com",
  "preferred_language": "vi",
  "role": "TRAVELER",
  "status": "ACTIVE",
  "created_at": "2026-06-09T08:30:00Z"
}
```

- Status codes:
  - `201 Created`: Dang ky thanh cong
  - `400 Bad Request`: Du lieu dau vao khong hop le
  - `409 Conflict`: Email da ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `VALIDATION_ERROR`
  - `EMAIL_ALREADY_EXISTS`

### 2. Login

- URL: `/api/v1/auth/login`
- Method: `POST`
- Auth required: No
- Headers:
  - `Content-Type: application/json`
- Request body:

```json
{
  "email": "an.nguyen@example.com",
  "password": "Password123!"
}
```

- Response body:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_value",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Nguyen Van An",
    "email": "an.nguyen@example.com",
    "role": "TRAVELER"
  }
}
```

- Status codes:
  - `200 OK`: Dang nhap thanh cong
  - `400 Bad Request`: Thieu email hoac password
  - `401 Unauthorized`: Sai email hoac mat khau
  - `423 Locked`: Tai khoan bi khoa
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `INVALID_CREDENTIALS`
  - `ACCOUNT_LOCKED`
  - `ACCOUNT_DISABLED`

### 3. Refresh Token

- URL: `/api/v1/auth/refresh`
- Method: `POST`
- Auth required: No
- Headers:
  - `Content-Type: application/json`
- Request body:

```json
{
  "refresh_token": "refresh_token_value"
}
```

- Response body:

```json
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "Bearer",
  "expires_in": 900
}
```

- Status codes:
  - `200 OK`: Cap token moi thanh cong
  - `400 Bad Request`: Request body khong hop le
  - `401 Unauthorized`: Refresh token khong hop le hoac het han
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `INVALID_REFRESH_TOKEN`
  - `REFRESH_TOKEN_EXPIRED`
  - `SESSION_REVOKED`

### 4. Logout

- URL: `/api/v1/auth/logout`
- Method: `POST`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- Request body:

```json
{
  "refresh_token": "refresh_token_value"
}
```

- Response body:

```json
{
  "message": "Logged out successfully"
}
```

- Status codes:
  - `200 OK`: Dang xuat thanh cong
  - `400 Bad Request`: Request body khong hop le
  - `401 Unauthorized`: Access token khong hop le
  - `404 Not Found`: Khong tim thay phien dang nhap
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `UNAUTHORIZED`
  - `SESSION_NOT_FOUND`

### 5. Get Current User

- URL: `/api/v1/auth/me`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Nguyen Van An",
  "email": "an.nguyen@example.com",
  "preferred_language": "vi",
  "role": "TRAVELER",
  "status": "ACTIVE",
  "created_at": "2026-06-09T08:30:00Z"
}
```

- Status codes:
  - `200 OK`: Lay thong tin user thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `404 Not Found`: User khong ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `UNAUTHORIZED`
  - `USER_NOT_FOUND`

## Upload Module

### 6. Upload Menu File

- URL: `/api/v1/uploads/menu`
- Method: `POST`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: multipart/form-data`
- Request body:
  - `file`: file anh/PDF menu, ho tro `image/jpeg`, `image/png`, `image/webp`, `application/pdf`
  - `target_language`: ngon ngu dich mong muon, vi du `vi`, `en`
- Response body:

```json
{
  "scan_session_id": "71151f64-39c7-4419-810a-c0835bafe341",
  "source_file_name": "menu-nha-hang.jpg",
  "source_mime_type": "image/jpeg",
  "source_file_size": 2458912,
  "target_language": "vi",
  "status": "PENDING",
  "created_at": "2026-06-09T08:35:00Z"
}
```

- Status codes:
  - `201 Created`: Upload thanh cong va tao scan session
  - `400 Bad Request`: File thieu hoac request khong hop le
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `413 Payload Too Large`: File vuot qua kich thuoc cho phep
  - `415 Unsupported Media Type`: Dinh dang file khong duoc ho tro
  - `500 Internal Server Error`: Loi upload file hoac storage
- Error codes:
  - `FILE_REQUIRED`
  - `UNSUPPORTED_FILE_TYPE`
  - `FILE_TOO_LARGE`
  - `STORAGE_UPLOAD_FAILED`

### 7. Get Upload Session

- URL: `/api/v1/uploads/{scan_session_id}`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "id": "71151f64-39c7-4419-810a-c0835bafe341",
  "source_file_name": "menu-nha-hang.jpg",
  "source_mime_type": "image/jpeg",
  "source_file_size": 2458912,
  "target_language": "vi",
  "status": "PROCESSING",
  "failure_reason": null,
  "created_at": "2026-06-09T08:35:00Z",
  "completed_at": null
}
```

- Status codes:
  - `200 OK`: Lay thong tin scan session thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Scan session khong thuoc user hien tai
  - `404 Not Found`: Scan session khong ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `UNAUTHORIZED`
  - `FORBIDDEN_SCAN_SESSION`
  - `SCAN_SESSION_NOT_FOUND`

### 8. Get Upload History

- URL: `/api/v1/uploads/history`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Query parameters:
  - `page`: so trang, mac dinh `1`
  - `page_size`: so ban ghi moi trang, mac dinh `20`
  - `status`: loc theo `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`
- Request body: None
- Response body:

```json
{
  "items": [
    {
      "id": "71151f64-39c7-4419-810a-c0835bafe341",
      "source_file_name": "menu-nha-hang.jpg",
      "target_language": "vi",
      "status": "COMPLETED",
      "created_at": "2026-06-09T08:35:00Z",
      "completed_at": "2026-06-09T08:35:12Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

- Status codes:
  - `200 OK`: Lay lich su upload thanh cong
  - `400 Bad Request`: Query parameter khong hop le
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `INVALID_PAGINATION`
  - `INVALID_SCAN_STATUS`

### 9. Delete Upload Session

- URL: `/api/v1/uploads/{scan_session_id}`
- Method: `DELETE`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "message": "Scan session deleted successfully"
}
```

- Status codes:
  - `200 OK`: Xoa lich su scan thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Scan session khong thuoc user hien tai
  - `404 Not Found`: Scan session khong ton tai
  - `409 Conflict`: Scan session dang duoc xu ly, chua the xoa
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `SCAN_SESSION_NOT_FOUND`
  - `SCAN_SESSION_PROCESSING`
  - `FORBIDDEN_SCAN_SESSION`

## OCR Module

### 10. Start OCR Processing

- URL: `/api/v1/ocr/scan-sessions/{scan_session_id}/process`
- Method: `POST`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- Request body:

```json
{
  "provider": "tesseract",
  "force_reprocess": false
}
```

- Response body:

```json
{
  "scan_session_id": "71151f64-39c7-4419-810a-c0835bafe341",
  "status": "PROCESSING",
  "message": "OCR processing started"
}
```

- Status codes:
  - `202 Accepted`: Da bat dau xu ly OCR
  - `400 Bad Request`: Request body khong hop le
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Scan session khong thuoc user hien tai
  - `404 Not Found`: Scan session khong ton tai
  - `409 Conflict`: Scan session da dang xu ly hoac da hoan thanh
  - `500 Internal Server Error`: Loi OCR provider
- Error codes:
  - `SCAN_SESSION_NOT_FOUND`
  - `OCR_ALREADY_PROCESSING`
  - `OCR_ALREADY_COMPLETED`
  - `OCR_PROVIDER_FAILED`

### 11. Get OCR Result

- URL: `/api/v1/ocr/scan-sessions/{scan_session_id}/result`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "id": "7bfc07df-e8b0-43dd-bbdd-f10463ef6985",
  "scan_session_id": "71151f64-39c7-4419-810a-c0835bafe341",
  "raw_text": "Pho Bo 60000 VND\nBun Cha 55000 VND",
  "confidence_score": 0.9475,
  "detected_language": "vi",
  "provider": "tesseract",
  "provider_metadata": {
    "page_count": 1,
    "processing_time_ms": 2400
  },
  "created_at": "2026-06-09T08:35:07Z"
}
```

- Status codes:
  - `200 OK`: Lay ket qua OCR thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Scan session khong thuoc user hien tai
  - `404 Not Found`: Chua co ket qua OCR hoac scan session khong ton tai
  - `409 Conflict`: OCR chua hoan thanh
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `OCR_RESULT_NOT_FOUND`
  - `OCR_NOT_COMPLETED`
  - `SCAN_SESSION_NOT_FOUND`

## Menu Module

### 12. Get Menus

- URL: `/api/v1/menus`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Query parameters:
  - `page`: so trang, mac dinh `1`
  - `page_size`: so ban ghi moi trang, mac dinh `20`
  - `is_saved`: loc menu da luu, vi du `true`
  - `q`: tu khoa tim kiem theo tieu de menu
- Request body: None
- Response body:

```json
{
  "items": [
    {
      "id": "d837618b-c842-4778-b0bb-d1178dcff634",
      "scan_session_id": "71151f64-39c7-4419-810a-c0835bafe341",
      "title": "Menu Nha hang Hoa Sen",
      "source_language": "vi",
      "target_language": "en",
      "default_currency": "VND",
      "is_saved": true,
      "created_at": "2026-06-09T08:35:10Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

- Status codes:
  - `200 OK`: Lay danh sach menu thanh cong
  - `400 Bad Request`: Query parameter khong hop le
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `INVALID_PAGINATION`
  - `INVALID_MENU_FILTER`

### 13. Get Menu Detail

- URL: `/api/v1/menus/{menu_id}`
- Method: `GET`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "id": "d837618b-c842-4778-b0bb-d1178dcff634",
  "scan_session_id": "71151f64-39c7-4419-810a-c0835bafe341",
  "title": "Menu Nha hang Hoa Sen",
  "source_language": "vi",
  "target_language": "en",
  "default_currency": "VND",
  "is_saved": true,
  "items": [
    {
      "id": "a2f20df8-5570-411d-aad6-59308a295f65",
      "original_name": "Pho bo",
      "translated_name": "Beef noodle soup",
      "original_description": "Pho voi thit bo tai",
      "translated_description": "Rice noodles with rare beef",
      "price": 60000.0,
      "currency": "VND",
      "confidence_score": 0.94,
      "sort_order": 1
    }
  ],
  "created_at": "2026-06-09T08:35:10Z"
}
```

- Status codes:
  - `200 OK`: Lay chi tiet menu thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Menu khong thuoc user hien tai
  - `404 Not Found`: Menu khong ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `MENU_NOT_FOUND`
  - `FORBIDDEN_MENU`

### 14. Save Menu

- URL: `/api/v1/menus/{menu_id}/save`
- Method: `PATCH`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- Request body:

```json
{
  "is_saved": true
}
```

- Response body:

```json
{
  "id": "d837618b-c842-4778-b0bb-d1178dcff634",
  "is_saved": true,
  "updated_at": "2026-06-09T08:40:00Z"
}
```

- Status codes:
  - `200 OK`: Cap nhat trang thai luu menu thanh cong
  - `400 Bad Request`: Request body khong hop le
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Menu khong thuoc user hien tai
  - `404 Not Found`: Menu khong ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `MENU_NOT_FOUND`
  - `FORBIDDEN_MENU`
  - `VALIDATION_ERROR`

### 15. Delete Menu

- URL: `/api/v1/menus/{menu_id}`
- Method: `DELETE`
- Auth required: Yes
- Headers:
  - `Authorization: Bearer <access_token>`
- Request body: None
- Response body:

```json
{
  "message": "Menu deleted successfully"
}
```

- Status codes:
  - `200 OK`: Xoa menu thanh cong
  - `401 Unauthorized`: Access token thieu hoac khong hop le
  - `403 Forbidden`: Menu khong thuoc user hien tai
  - `404 Not Found`: Menu khong ton tai
  - `500 Internal Server Error`: Loi he thong
- Error codes:
  - `MENU_NOT_FOUND`
  - `FORBIDDEN_MENU`

## Existing Health Endpoints

Hai endpoint sau da co trong backend hien tai va khong thuoc 4 module nghiep vu cua task.

### Root

- URL: `/`
- Method: `GET`
- Auth required: No
- Headers: None
- Request body: None
- Response body:

```json
{
  "message": "MenuScan API is running!"
}
```

- Status codes:
  - `200 OK`: API dang chay

### Health Check

- URL: `/health`
- Method: `GET`
- Auth required: No
- Headers: None
- Request body: None
- Response body:

```json
{
  "status": "ok"
}
```

- Status codes:
  - `200 OK`: Service san sang nhan request
