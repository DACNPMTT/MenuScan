# Diagram status

Toàn bộ sơ đồ trong thư mục này đã được **vẽ lại theo code thực tế** (migration
head `e8b5d3f07a24`, 7 module backend, 48 endpoint dưới `/api/v1`, 20 bảng).
Chúng khớp với code và dùng được làm tài liệu nộp.

## Sinh lại bằng script

| Sơ đồ | Cách sinh lại |
| --- | --- |
| `ERD Diagram.drawio` | `cd app && .venv/Scripts/python.exe ../doc/diagrams/generate_erd.py` |
| Các sơ đồ còn lại | Sửa trực tiếp trong Draw.io |

ERD được **sinh từ SQLAlchemy metadata**, không vẽ tay — chạy lại script sau mỗi
migration mới thì nó không thể lệch khỏi code được nữa. Trước đây ERD vẽ tay và
đã đóng băng ở revision `001` (7 bảng) trong khi schema đã lên 20 bảng.

## Sequence và Activity diagram

5 sequence diagram và 4 activity diagram là **Mermaid nhúng trong Draw.io**: file
`.drawio` chứa cả mermaid source (thuộc tính `mermaidData`) lẫn ảnh SVG đã render.

Muốn sửa: mở file trong Draw.io, chuột phải vào hình → **Edit** → sửa mermaid →
Draw.io tự render lại. Nếu chỉ sửa `mermaidData` bằng tay trong file XML thì ảnh
SVG vẫn là bản cũ — phải re-render, nếu không sơ đồ sẽ hiển thị sai so với source.

## Ràng buộc kiến trúc mà sơ đồ phải tôn trọng

Các sơ đồ cũ từng vẽ những thứ **không tồn tại trong code**. Khi sửa sơ đồ, đừng
đưa chúng trở lại:

- **Không có Vector DB / RAG engine.** Gợi ý món được chấm bằng luật trên
  preference của participant trong dining session, không phải retrieval trên
  embedding.
- **Không dùng Redis.** `docker-compose.yml` có container Redis nhưng không dòng
  code nào dùng. Anti-spam throttle nằm ở bảng `ai_throttle` trong Postgres
  (`app/src/core/rate_limit.py`).
- **Không có worker queue / Celery.** Job nền duy nhất là
  `run_stale_scan_watchdog`.
- **Không có admin dashboard.**
- **Không có tìm kiếm toàn cục.** `search` chỉ lọc món bên trong một menu
  (`GET /menus/{id}/items?search=`).
- Endpoint scan là `POST /api/v1/scans` (không phải `/menu-scans`); không tồn tại
  endpoint `/user-food-actions`.
- Các class `SearchService`, `HistoryService`, `MenuAnalysisService`, `ScanRouter`
  trong sơ đồ cũ **không tồn tại**. Ngược lại, `OcrService`, `MenuParser` và
  `TranslationService` là **có thật** — chúng nằm trong `modules/menu_scan/` và là
  cộng tác viên của `ScanPipeline`.

## Nguồn hiện hành

- [MVP Contract](../content/mvp-contract.md)
- [SRS](../content/SRS.md)
- [API](../content/api-endpoints.md)
- [Database specification](../content/specification/database.md)
- [Use cases](../content/specification/usecase.md)

Alembic migration là nguồn schema thực thi duy nhất; ERD và `DB/schema.sql` chỉ
là bản trình bày được sinh ra từ đó.
