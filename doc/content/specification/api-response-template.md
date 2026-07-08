# MenuScan API Response Standard

> Nguồn nghiệp vụ chuẩn: [MenuScan MVP Contract](../mvp-contract.md)

## Success

```json
{
  "success": true,
  "data": {},
  "meta": null
}
```

- `data`: object, array hoặc `null`.
- `meta`: metadata như pagination; `null` nếu không dùng.
- HTTP status chỉ nằm ở status line, không lặp trong body.
- Response `204 No Content` không có body.

## Error

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

- `code`: mã ổn định để frontend xử lý.
- `message`: thông điệp an toàn có thể hiển thị.
- `details`: `null` hoặc dữ liệu bổ sung có cấu trúc.
- `request_id`: dùng đối chiếu log.
- Không trả raw exception, stack trace, token hoặc secret.

## Status code

| HTTP | Dùng khi |
| --- | --- |
| `200` | Đọc hoặc cập nhật thành công. |
| `202` | Đã nhận yêu cầu xử lý bất đồng bộ hoặc gửi email. |
| `204` | Logout thành công, không có body. |
| `400` | Request không hợp lệ hoặc Magic Link sai. |
| `401` | Chưa đăng nhập, link/session hết hạn. |
| `403` | User không sở hữu tài nguyên. |
| `404` | Không tìm thấy tài nguyên. |
| `409` | Trạng thái tài nguyên chưa cho phép thao tác. |
| `413` | File vượt quá 10 MB. |
| `415` | MIME type không hỗ trợ. |
| `422` | File hợp lệ về định dạng nhưng không thể xử lý. |
| `429` | Vượt rate limit. |
| `500` | Lỗi không dự kiến. |
| `503` | Dịch vụ phụ thuộc tạm thời không sẵn sàng. |

## Pagination

```json
{
  "success": true,
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 0,
    "total_pages": 0
  }
}
```
