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
        "allergies": [],
        "dietary_preferences": [],
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
    "allergies": [],
    "dietary_preferences": [],
    "role": "USER",
    "status": "ACTIVE",
    "created_at": "2026-06-20T08:30:00Z"
  },
  "meta": null
}
```

### POST `/auth/login`

Đăng nhập bằng email và mật khẩu. Chỉ dùng được sau khi user đã đặt mật khẩu
qua `/auth/set-password`. Sai email/mật khẩu hoặc user chưa đặt mật khẩu đều trả
lỗi xác thực chung.

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Response `200 OK`: cùng shape với `POST /auth/magic-links/verify` (access token,
user object, refresh cookie).

Lỗi: `401 INVALID_CREDENTIALS`, `400 VALIDATION_ERROR`.

### POST `/auth/set-password`

Auth bắt buộc. Đặt hoặc đổi mật khẩu cho user hiện tại. Mật khẩu lưu dưới dạng
bcrypt hash.

```json
{
  "password": "new-password"
}
```

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "message": "Password set successfully."
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`.

### PATCH `/auth/me`

Auth bắt buộc. Cập nhật profile user hiện tại.

```json
{
  "display_name": "Nguyễn Văn A",
  "preferred_language": "en",
  "allergies": ["seafood", "peanut"],
  "dietary_preferences": ["no_pork"]
}
```

Tất cả trường đều optional. `preferred_language` chỉ chấp nhận `vi` hoặc `en`.
`allergies` validate theo tập: `seafood`, `shellfish`, `fish`, `peanut`,
`tree_nut`, `egg`, `dairy`, `gluten`, `soy`, `sesame`. `dietary_preferences`
validate theo tập: `vegetarian`, `vegan`, `no_pork`, `no_beef`, `no_alcohol`.

Response `200 OK`: cùng shape với `GET /auth/me`.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`.

### POST `/auth/me/profile`

Auth bắt buộc. Tương đương `PATCH /auth/me` — bản POST cho client hoặc proxy
chặn PATCH. Cùng body và response.

### GET `/auth/me/food-profiles`

Auth bắt buộc. Trả danh sách hồ sơ ăn uống lâu dài của user hiện tại.

Response `200 OK`:

```json
{
  "success": true,
  "data": [
    {
      "id": "3b9f3a0a-2b75-4f3b-9f1d-6db8c9f3f0e2",
      "user_id": "83a473bd-0e40-4af6-a96c-4e0bd3dd6145",
      "display_name": "My food profile",
      "preferred_language": "en",
      "is_default": true,
      "notes": null,
      "preferences": [
        {
          "id": "cba521bf-7339-4442-99b8-190e4d67a3f5",
          "code": "seafood",
          "category": "allergen",
          "preference_type": "ALLERGY",
          "intensity": null,
          "importance": 5,
          "note": null,
          "created_at": "2026-07-11T14:00:00Z"
        }
      ],
      "created_at": "2026-07-11T14:00:00Z",
      "updated_at": "2026-07-11T14:00:00Z"
    }
  ],
  "meta": null
}
```

### POST `/auth/me/food-profiles`

Auth bắt buộc. Tạo hồ sơ ăn uống. Nếu đây là profile đầu tiên của user thì hệ
thống tự đặt `is_default = true`.

```json
{
  "display_name": "My food profile",
  "preferred_language": "en",
  "is_default": true,
  "notes": null,
  "preferences": [
    {
      "code": "seafood",
      "category": "allergen",
      "preference_type": "ALLERGY",
      "intensity": null,
      "importance": 5,
      "note": null
    },
    {
      "code": "no_pork",
      "category": "dietary",
      "preference_type": "DIETARY_RULE",
      "importance": 4
    }
  ]
}
```

`preference_type` nhận: `LIKE`, `DISLIKE`, `AVOID`, `ALLERGY`,
`DIETARY_RULE`. `intensity` nằm trong `0..5`; `importance` nằm trong `1..5`.

Response `201 Created`: một food profile cùng shape item trong
`GET /auth/me/food-profiles`.

### GET `/auth/me/food-profiles/{profile_id}`

Auth bắt buộc. Lấy một hồ sơ ăn uống thuộc user hiện tại.

Lỗi: `401 UNAUTHORIZED`, `404 FOOD_PROFILE_NOT_FOUND`.

### PATCH `/auth/me/food-profiles/{profile_id}`

Auth bắt buộc. Cập nhật hồ sơ ăn uống. Tất cả trường optional; nếu gửi
`preferences` thì backend thay thế toàn bộ danh sách preference của profile đó.
Nếu đặt `is_default = true`, các profile khác của user sẽ tự bỏ default.

Response `200 OK`: một food profile cùng shape item trong
`GET /auth/me/food-profiles`.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `404 FOOD_PROFILE_NOT_FOUND`.

### DELETE `/auth/me/food-profiles/{profile_id}`

Auth bắt buộc. Soft-delete một hồ sơ ăn uống. Nếu profile bị xóa là default,
backend chọn profile còn lại đầu tiên làm default; nếu không còn profile nào thì
`users.allergies` và `users.dietary_preferences` được reset về rỗng để tương
thích luồng cũ.

Response `204 No Content`.

## 3. Scan

### GET `/scans`

Auth bắt buộc. Trả danh sách phiên scan của user hiện tại, mới nhất trước.

Query:

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `page` | Không | Số trang, mặc định `1`, tối thiểu `1` |
| `page_size` | Không | Số item mỗi trang, mặc định `20`, tối đa `50` |

Response `200 OK`:

```json
{
  "success": true,
  "data": [
    {
      "id": "71151f64-39c7-4419-810a-c0835bafe341",
      "status": "COMPLETED",
      "created_at": "2026-06-20T08:35:00Z",
      "completed_at": "2026-06-20T08:36:30Z",
      "source": {
        "file_name": "menu.jpg",
        "mime_type": "image/jpeg",
        "file_size": 2458912,
        "preview_url": "/api/v1/scans/71151f64-39c7-4419-810a-c0835bafe341/source"
      },
      "menu": {
        "id": "d837618b-c842-4778-b0bb-d1178dcff634",
        "title": "Menu Nhà hàng Hoa Sen",
        "is_saved": true,
        "item_count": 12
      }
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

`menu` là `null` nếu phiên scan chưa có menu.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`.

### POST `/scans`

Auth không bắt buộc. User đã đăng nhập sẽ có lịch sử scan; guest vẫn tạo được
scan nhưng không xuất hiện trong `GET /scans`. Content-Type `multipart/form-data`.

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `files` | Không | Danh sách JPG/JPEG/PNG/WEBP/PDF; mỗi file tối đa 10 MB; tổng payload tối đa 40 MB; tổng số trang tối đa 8 |
| `file` | Không | Trường legacy cho một file; nếu gửi cùng `files` thì được nối vào cuối danh sách |
| `target_language` | Không | Language tag chữ thường như `vi`, `en`, `zh`, `pt-br`; tối đa 10 ký tự; mặc định theo user, fallback `vi` |

Request phải có ít nhất một file. Backend xác thực MIME từ bytes thật, không tin
tên file hoặc `Content-Type` client gửi.

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

Lỗi: `400 EMPTY_FILE`, `400 VALIDATION_ERROR`, `413 FILE_TOO_LARGE`,
`415 UNSUPPORTED_FILE_TYPE`, `422 INVALID_PDF`, `422 TOO_MANY_PAGES`,
`503 STORAGE_UNAVAILABLE`.

### GET `/scans/{scan_id}`

Auth không bắt buộc. Scan có `user_id` chỉ owner được truy cập; guest scan có
thể được đọc bằng `scan_id`.

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

`progress` chỉ dùng hiển thị và nằm trong `0..100`. `stage` có thể là `null`
hoặc một trong `OCR`, `ANALYZING`, `TRANSLATING`, `FINALIZING`.

Lỗi: `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`.

### GET `/scans/{scan_id}/source`

Auth không bắt buộc theo cùng quy tắc truy cập của `GET /scans/{scan_id}`. Trả file gốc hoặc `302` đến signed URL sống ngắn. Response phải
có đúng `Content-Type`; PDF hiển thị bằng PDF viewer, ảnh hiển thị bằng image
preview.

Lỗi: `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`,
`404 SOURCE_FILE_NOT_FOUND`.

### GET `/scans/{scan_id}/result`

Auth không bắt buộc theo cùng quy tắc truy cập của `GET /scans/{scan_id}`. Chỉ
gọi khi status là `COMPLETED`.

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

Lỗi: `403 FORBIDDEN`, `404 SCAN_NOT_FOUND`, `409 SCAN_NOT_READY`.

## 4. Bill

> Nghiệp vụ domain: xem `src/modules/billing/service.py` (issue #127, #128, #129).

### POST `/bills`

Auth bắt buộc. Tạo hóa đơn `DRAFT` rỗng, gắn với menu của chính user.

```json
{
  "menu_id": "d837618b-c842-4778-b0bb-d1178dcff634"
}
```

Response `201 Created`:

```json
{
  "success": true,
  "data": {
    "id": "9b2f5e2a-2222-4444-8888-000000000001",
    "user_id": "0f1a2b3c-...",
    "menu_id": "d837618b-c842-4778-b0bb-d1178dcff634",
    "status": "DRAFT",
    "currency": "VND",
    "subtotal_amount": "0.00",
    "adjustment_total": "0.00",
    "total_amount": "0.00",
    "note": null,
    "items": [],
    "adjustments": [],
    "created_at": "2026-06-30T08:30:00Z",
    "updated_at": "2026-06-30T08:30:00Z",
    "finalized_at": null
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `404 MENU_NOT_FOUND`.

### GET `/bills/{bill_id}`

Auth bắt buộc. Chỉ owner được truy cập; not-found và not-owned đều trả về
`404 BILL_NOT_FOUND` để không lộ sự tồn tại của hóa đơn cho người khác.

Response `200 OK`: cùng shape với `POST /bills`, với `items` và `adjustments`
đầy đủ.

Lỗi: `401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`.

### PATCH `/bills/{bill_id}/items`

Auth bắt buộc. Chỉ owner và chỉ khi bill đang `DRAFT` mới được sửa. Body là
**trạng thái mong muốn cuối cùng** của toàn bộ danh sách item trên hóa đơn.
Client chỉ gửi `food_item_id` và `quantity`; server luôn tự đọc giá hiện tại
và tính lại tất cả totals.

```json
{
  "items": [
    { "food_item_id": "a2f20df8-5570-411d-aad6-59308a295f65", "quantity": 2 },
    { "food_item_id": "b3f31ef9-6681-522e-bbe7-6a419b3a6076", "quantity": 1 }
  ]
}
```

Response `200 OK`: cùng shape với `GET /bills/{bill_id}`.

Lỗi: `400 VALIDATION_ERROR`, `400 CURRENCY_MISMATCH`, `400 FOOD_ITEM_MISSING_PRICE`,
`401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`, `404 FOOD_ITEM_NOT_FOUND`,
`409 BILL_ALREADY_FINALIZED`.

### POST `/bills/{bill_id}/adjustments`

Auth bắt buộc. Chỉ owner, chỉ bill `DRAFT`. Thêm một khoản điều chỉnh
(phí, thuế, giảm giá, phụ thu) và tính lại `adjustment_total` / `total_amount`.

**Loại adjustment** (`type`): `DISCOUNT` · `TAX` · `SERVICE_CHARGE` ·
`SURCHARGE` · `ROUNDING`.

**Cách tính** (`calculation_type`): `FIXED` (số tiền cố định) hoặc
`PERCENTAGE` (% của `subtotal_amount`).

**Quy tắc thứ tự tính (ordering rule)**: mỗi adjustment — dù FIXED hay
PERCENTAGE — được tính **độc lập** từ `subtotal_amount` gốc, không cộng dồn
trên running total của các adjustment khác. Điều này đảm bảo kết quả không
phụ thuộc vào thứ tự thêm adjustment và mỗi dòng trên receipt hiển thị đúng
`calculated_amount` của chính nó.

Server tự tính `calculated_amount` (có dấu: âm cho DISCOUNT, dương cho các
loại còn lại) -- client chỉ gửi `value` không dấu.

```json
{
  "type": "TAX",
  "calculation_type": "PERCENTAGE",
  "label": "VAT 10%",
  "value": "10"
}
```

Response `201 Created`: full bill với `adjustments` đã có khoản mới.

```json
{
  "id": "c3d4e5f6-...",
  "type": "TAX",
  "calculation_type": "PERCENTAGE",
  "label": "VAT 10%",
  "value": "10.00",
  "calculated_amount": "6500.00",
  "created_at": "2026-06-30T09:00:00Z"
}
```

Lỗi: `400 VALIDATION_ERROR`, `400 INVALID_ADJUSTMENT_VALUE`,
`400 INVALID_PERCENTAGE_RANGE` (value > 100), `400 ADJUSTMENT_LABEL_REQUIRED`,
`400 NEGATIVE_TOTAL` (discount làm total < 0),
`401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`, `409 BILL_ALREADY_FINALIZED`.

### PATCH `/bills/{bill_id}/adjustments/{adjustment_id}`

Auth bắt buộc. Chỉ owner, chỉ bill `DRAFT`. Sửa toàn bộ trường của adjustment
và tính lại totals. Body giống `POST /bills/{bill_id}/adjustments`.

Response `200 OK`: full bill sau khi cập nhật.

Lỗi: giống POST adjustments, thêm `404 ADJUSTMENT_NOT_FOUND`.

### DELETE `/bills/{bill_id}/adjustments/{adjustment_id}`

Auth bắt buộc. Chỉ owner, chỉ bill `DRAFT`. Xóa adjustment và tính lại totals.

Response `200 OK`: full bill sau khi xóa.

Lỗi: `401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`, `404 ADJUSTMENT_NOT_FOUND`,
`409 BILL_ALREADY_FINALIZED`.

### POST `/bills/{bill_id}/finalize`

Auth bắt buộc. Chỉ owner. Chốt bill `DRAFT` thành `FINALIZED` — bill phải có
ít nhất một item. Sau khi finalize, mọi thao tác thêm/sửa/xóa item hoặc
adjustment đều bị từ chối với `409 BILL_ALREADY_FINALIZED`.

Response `200 OK`: full bill với `status: "FINALIZED"` và `finalized_at` được
set server-side.

Lỗi: `400 EMPTY_BILL`, `401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`,
`409 BILL_ALREADY_FINALIZED`.

### POST `/bills/{bill_id}/split`

Auth bắt buộc. Chỉ owner. Chia đều `total_amount` của bill cho `people_count`
người. Toàn bộ tính toán dùng `Decimal`, không dùng floating-point: phần cơ bản
mỗi người được floor đến cent, phần dư (theo nguyên cent) được phân bổ
deterministic cho những người đầu tiên, nên tổng các phần luôn bằng đúng
`total_amount` — không mất tiền do làm tròn. Bill không bị thay đổi (cả DRAFT
và FINALIZED đều chia được); split là phép tính lại dựa trên item/adjustment
hiện tại (xem `src/modules/billing/service.py`, issue #129).

Body:

```json
{
  "people_count": 3
}
```

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "bill_id": "9b1c...",
    "currency": "USD",
    "total_amount": "100.00",
    "people_count": 3,
    "base_share": "33.33",
    "remainder_units": 1,
    "shares": [
      { "person": 1, "amount": "33.34" },
      { "person": 2, "amount": "33.33" },
      { "person": 3, "amount": "33.33" }
    ]
  },
  "meta": null
}
```

Lỗi: `400 VALIDATION_ERROR` (`people_count < 1`), `400 INVALID_PEOPLE_COUNT`,
`401 UNAUTHORIZED`, `404 BILL_NOT_FOUND`.

## 5. Menu

### GET `/menus`

Auth bắt buộc. Trả danh sách menu của user, mới nhất trước.

Query:

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `page` | Không | Số trang, mặc định `1`, tối thiểu `1` |
| `page_size` | Không | Số item mỗi trang, mặc định `20`, tối đa `50` |

Response `200 OK`:

```json
{
  "success": true,
  "data": [
    {
      "id": "d837618b-c842-4778-b0bb-d1178dcff634",
      "title": "Menu Nhà hàng Hoa Sen",
      "status": "DRAFT",
      "is_saved": true,
      "item_count": 12,
      "default_currency": "VND",
      "source": {
        "scan_id": "71151f64-39c7-4419-810a-c0835bafe341",
        "file_name": "menu.jpg",
        "mime_type": "image/jpeg",
        "file_size": 2458912,
        "preview_url": "/api/v1/scans/71151f64-39c7-4419-810a-c0835bafe341/source"
      },
      "created_at": "2026-06-20T08:35:00Z",
      "updated_at": "2026-06-20T08:40:00Z",
      "confirmed_at": null
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

Lỗi: `401 UNAUTHORIZED`.

### GET `/menus/{menu_id}`

Auth bắt buộc. Trả chi tiết menu bao gồm danh sách món.

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "id": "d837618b-c842-4778-b0bb-d1178dcff634",
    "title": "Menu Nhà hàng Hoa Sen",
    "status": "DRAFT",
    "is_saved": true,
    "source_language": "vi",
    "target_language": "en",
    "default_currency": "VND",
    "source": {
      "scan_id": "71151f64-39c7-4419-810a-c0835bafe341",
      "file_name": "menu.jpg",
      "mime_type": "image/jpeg",
      "file_size": 2458912,
      "preview_url": "/api/v1/scans/71151f64-39c7-4419-810a-c0835bafe341/source"
    },
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
    ],
    "created_at": "2026-06-20T08:35:00Z",
    "updated_at": "2026-06-20T08:40:00Z",
    "confirmed_at": null
  },
  "meta": null
}
```

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 MENU_NOT_FOUND`.

### GET `/menus/{menu_id}/items`

Auth bắt buộc. Trả danh sách món với tìm kiếm và lọc.

Query:

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `search` | Không | Tìm theo `original_name` hoặc `translated_name` (case-insensitive LIKE) |
| `min_price` | Không | Giá tối thiểu, `>=0` |
| `max_price` | Không | Giá tối đa, `>=0`, phải `>= min_price` |
| `page` | Không | Số trang, mặc định `1` |
| `page_size` | Không | Số item mỗi trang, mặc định `20`, tối đa `50` |

Response `200 OK`: danh sách `MenuItemResponse` với pagination meta.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `403 FORBIDDEN`,
`404 MENU_NOT_FOUND`.

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

### POST `/menus/{menu_id}/confirm`

Auth bắt buộc. Chuyển menu từ `DRAFT` sang `CONFIRMED`, tự động đánh dấu
`is_saved = true`.

Response `200 OK`: cùng shape với `GET /menus/{menu_id}`.

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 MENU_NOT_FOUND`.

### POST `/menus/{menu_id}/items`

Auth bắt buộc. Thêm một món thủ công vào menu.

```json
{
  "original_name": "Cơm tấm",
  "translated_name": "Broken rice",
  "original_description": null,
  "translated_description": null,
  "price": "45000.00",
  "currency": "VND",
  "category": "Cơm"
}
```

Response `201 Created`: `MenuItemResponse`.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `403 FORBIDDEN`,
`404 MENU_NOT_FOUND`.

### PATCH `/menus/{menu_id}/items/{item_id}`

Auth bắt buộc. Sửa một món. Body giống `POST` nhưng tất cả trường đều optional
(partial update).

Response `200 OK`: `MenuItemResponse`.

Lỗi: `400 VALIDATION_ERROR`, `401 UNAUTHORIZED`, `403 FORBIDDEN`,
`404 MENU_NOT_FOUND`, `404 MENU_ITEM_NOT_FOUND`.

### DELETE `/menus/{menu_id}/items/{item_id}`

Auth bắt buộc. Xóa một món.

Response `204 No Content`.

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 MENU_NOT_FOUND`,
`404 MENU_ITEM_NOT_FOUND`.

### DELETE `/menus/{menu_id}`

Auth bắt buộc. Soft-delete menu và phiên scan liên quan.

Response `204 No Content`.

Lỗi: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 MENU_NOT_FOUND`.

## 6. Exchange Rate

### GET `/exchange-rates`

Auth không bắt buộc. Trả tỷ giá quy đổi theo đồng tiền cơ sở.

Query:

| Field | Bắt buộc | Giá trị |
| --- | --- | --- |
| `base` | Không | Mã tiền tệ 3 ký tự, mặc định `VND` |

Response `200 OK`:

```json
{
  "success": true,
  "data": {
    "base": "VND",
    "rates": {
      "USD": 0.00004,
      "EUR": 0.000037
    },
    "updated_at": "2026-06-20T08:00:00Z"
  },
  "meta": null
}
```

Backend proxy nhà cung cấp tỷ giá bên ngoài và cache trong tiến trình theo TTL.
Khi upstream lỗi trả `503 DEPENDENCY_UNAVAILABLE`.

## 7. Endpoint nội bộ

OCR, parser và translation là module nội bộ do Scan service điều phối. MVP
không công khai endpoint để frontend chọn provider hoặc tự bắt đầu OCR.

## 8. Health

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
