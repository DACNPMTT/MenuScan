# Diagram status

Các file Draw.io trong thư mục này được tạo trước khi phạm vi MVP và Magic Link
được chốt. Chúng chỉ là tài liệu tham khảo lịch sử và không được dùng làm nguồn
để triển khai auth, upload, database hoặc API.

## ERD hiện hành

- [ERD Diagram.drawio](ERD%20Diagram.drawio) mô tả bảy bảng trong Alembic
  revision `001_create_mvp_schema`.
- Alembic migration là nguồn schema thực thi duy nhất; ERD được duy trì để trình
  bày schema, không thay thế migration.

## Nguồn hiện hành

- [MVP Contract](../content/mvp-contract.md)
- [SRS](../content/SRS.md)
- [API](../content/api-endpoints.md)
- [Database specification](../content/specification/database.md)

Các sơ đồ auth, upload, use case và class cần được vẽ lại sau khi team
review contract. Khi sơ đồ mới được merge, file cũ tương ứng phải được thay thế
hoặc xóa để tránh tồn tại hai mô tả nghiệp vụ.
