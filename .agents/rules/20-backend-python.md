# Backend Rules — Python and FastAPI

Áp dụng cho `app/`, worker và code tích hợp OCR/provider.

## Cấu trúc và Python

- Hỗ trợ Python 3.12+. Router chỉ parse/validate request, gọi service và
  map response; business logic không nằm trong route handler.
- Tổ chức backend theo modular layered architecture, không mặc định áp dụng DDD,
  Clean Architecture, CQRS hoặc event-driven architecture.
- Mỗi module ưu tiên cấu trúc phẳng `router`, `schemas`, `service`, `repository`,
  `models`; chỉ tách package khi file thực sự có nhiều responsibility.
- Tách data access khỏi service; inject dependency để test được và tránh global
  mutable request state.
- Dùng type hints cho public function và boundary. Không bắt `Exception` rồi bỏ
  qua; map lỗi dự kiến thành API error ổn định, log lỗi bất ngờ an toàn với
  request ID.
- I/O dùng async xuyên suốt khi dependency hỗ trợ. Không chạy CPU-bound OCR hoặc
  blocking SDK trên event loop. Upload tạo scan rồi xử lý bất đồng bộ theo
  contract.

## Python convention

- Tuân PEP 8 và Ruff: module/function/variable `snake_case`; class, exception,
  Pydantic/SQLAlchemy model `PascalCase`; constant `UPPER_SNAKE_CASE`.
- Dùng absolute import từ package ứng dụng; không sửa `sys.path` trong source.
- Public function/method có type hint cụ thể; dùng `X | None` và collection
  built-in trên Python 3.12.
- Pydantic request/response/service DTO tách khi responsibility khác nhau; mutable
  default dùng `default_factory`.
- Module exception kết thúc bằng `Error`; chỉ bắt lỗi có thể xử lý và dùng
  `raise ... from error` khi chuyển tầng.
- Route function đặt theo hành động nghiệp vụ; dependency là `get_*` hoặc
  `require_*`. Docstring chỉ cho public contract/logic không hiển nhiên.

## FastAPI/API

- Public route MVP ở `/api/v1`; `/health` chỉ phản ánh process, `/ready` kiểm tra
  dependency. Không để health check phụ thuộc DB.
- Validate input ở boundary, business rule trong service và constraint bền vững
  trong DB. Không tin filename hoặc `Content-Type`; xác minh nội dung, size và
  page count.
- Trả wrapper chuẩn, trừ `204` hoặc file/redirect theo contract. Không trả ORM
  object, stack trace, raw provider response hay secret.
- Authenticated query luôn scope theo current user, tránh fetch trước rồi mới che
  dữ liệu ở response.

## Data và transaction

- Dùng SQLAlchemy 2.x style; không nối SQL từ input. Transaction bao trọn invariant
  như consume Magic Link + tạo session và refresh-token rotation.
- Không giữ DB transaction mở qua external call nếu có thể tách pha an toàn.
- Operation có thể retry phải idempotent hoặc có guard; scan terminal state không
  được cập nhật ngược.

## Kiểm tra

- Chạy trong `app/`: `uv run ruff check .` và `uv run pytest`.
- Test happy path, validation/error mapping, authorization/ownership và transaction
  invariant; mock external provider, không mock business logic đang test.
