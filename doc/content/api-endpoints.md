# MenuScan MVP API

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](./mvp-contract.md)

- Base URL: `/api/v1`
- JSON: `application/json`
- Auth: `Authorization: Bearer <access_token>`
- Thời gian: ISO 8601 UTC
- ID: UUID
- Tiền: chuỗi decimal, ví dụ `"60000.00"`

## 1. Response wrapper

```json
{
  "success": true,
  "data": {},
  "meta": null
}
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dữ liệu không hợp lệ.",
    "details": {
      "fields": {
        "email": ["Email không đúng định dạng."]
      }
    },
    "request_id": "req_01J..."
  }
}
```

## 2. Auth

### POST `/auth/magic-links`

Gửi Magic Link. API luôn trả cùng một response dù email mới hay đã tồn tại.

```json
{
  "email": "user@example.com"
}
```

Response `202 Accepted`:

```json
{
  "success": true,
  "data": {
    "message": "Nếu email hợp lệ, liên kết đăng nhập sẽ được gửi.",
    "resend_after_seconds": 60
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR`, `429 RATE_LIMITED`,
`503 EMAIL_SERVICE_UNAVAILABLE`.

### POST `/auth/magic-links/verify`

Xác minh token dùng một lần. Nếu email chưa có user, hệ thống tự tạo user.
Refresh token được set bằng cookie `HttpOnly`, không trả trong JSON.

```json
{
  "token": "raw-token-from-email"
}
```

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "display_name": null,
      "preferred_language": "vi",
      "role": "USER"
    }
  },
  "meta": null
}
```

Lỗi: `400 INVALID_MAGIC_LINK`, `401 MAGIC_LINK_EXPIRED`.

### POST `/auth/refresh`

Đọc refresh cookie, rotate session và set cookie mới. Request không có body.

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 900
  },
  "meta": null
}
```

Lỗi: `401 SESSION_EXPIRED`, `401 SESSION_REVOKED`.

### POST `/auth/logout`

Auth bắt buộc. Thu hồi session hiện tại và xóa refresh cookie.

Response `204 No Content`.

### GET `/auth/me`

Auth bắt buộc.

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": null,
    "preferred_language": "vi",
    "role": "USER",
    "status": "ACTIVE",
    "created_at": "2026-06-20T08:30:00Z"
  },
  "meta": null
}
```

## 3. Scan

### POST `/scans`

Auth bắt buộc. Content-Type `multipart/form-data`.

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `file` | Có | Một JPG/JPEG/PNG/WEBP/PDF, tối đa 10 MB; PDF tối đa 5 trang |
| `target_language` | Không | `vi` hoặc `en`; mặc định theo user, fallback `en` cho khách nước ngoài |

Response `202 Accepted`:

```json
{
  "success": true,
  "data": {
    "id": "71151f64-39c7-4419-810a-c0835bafe341",
    "status": "PENDING",
    "progress": 0,
    "source": {
      "file_name": "menu.jpg",
      "mime_type": "image/jpeg",
      "file_size": 2458912
    },
    "target_language": "en",
    "created_at": "2026-06-20T08:35:00Z"
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `413 FILE_TOO_LARGE`,
`415 UNSUPPORTED_FILE_TYPE`, `422 INVALID_PDF`.

### GET `/scans/{scan_id}`

Auth bắt buộc. Chỉ owner được truy cập.

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": "71151f64-39c7-4419-810a-c0835bafe341",
    "status": "PROCESSING",
    "stage": "ANALYZING",
    "progress": 65,
    "error": null,
    "created_at": "2026-06-20T08:35:00Z",
    "completed_at": null
  },
  "meta": null
}
```

`progress` chỉ dùng hiển thị và nằm trong `0..100`. `stage` có thể là
`UPLOADING`, `OCR`, `ANALYZING`, `TRANSLATING`, `FINALIZING`.

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`.

### GET `/scans/{scan_id}/source`

Auth bắt buộc. Trả file gốc hoặc `302` đến signed URL sống ngắn. Response phải
có đúng `Content-Type`; PDF hiển thị bằng PDF viewer, ảnh hiển thị bằng image
preview.

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`,
`404 SOURCE_FILE_NOT_FOUND`.

### GET `/scans/{scan_id}/result`

Auth bắt buộc. Chỉ gọi khi status là `COMPLETED`.

Response `200 OK`:

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

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`,
`409 SCAN_NOT_READY`.

## 4. Menu

### PATCH `/menus/{menu_id}`

Auth bắt buộc. Xác nhận lưu hoặc bỏ lưu menu.

```json
{
  "is_saved": true
}
```

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": "d837618b-c842-4778-b0bb-d1178dcff634",
    "is_saved": true,
    "updated_at": "2026-06-20T08:40:00Z"
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `403 FORBIDDEN`,
`404 MENU_NOT_FOUND`.

## 5. Endpoint nội bộ

OCR, parser và translation là module nội bộ do Scan service điều phối. MVP
không công khai endpoint để frontend chọn provider hoặc tự bắt đầu OCR.

## 6. Health

- `GET /health`: process API đang chạy, không phụ thuộc database.
- `GET /ready`: API và database đã sẵn sàng nhận request.

`GET /health` trả `200 OK`:

```json
{
  "status": "ok"
}
```

`GET /ready` trả `200 OK` khi PostgreSQL kết nối được:

```json
{
  "status": "ready",
  "database": "ok"
}
```

Khi PostgreSQL không sẵn sàng, `/ready` trả `503 DEPENDENCY_UNAVAILABLE` theo
error wrapper chuẩn. Mọi response có header `X-Request-ID`.
