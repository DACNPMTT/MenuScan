# Testing and Documentation Rules

## Chiến lược test

- Test theo hành vi và contract, không khóa vào implementation detail.
- Mỗi bug fix cần regression test tái hiện lỗi trước khi sửa khi khả thi.
- Ưu tiên unit test cho service/utility, integration test cho API + DB/cache
  boundary, và ít end-to-end test cho luồng Magic Link/scan cốt lõi.
- Test phải deterministic: không phụ thuộc thời gian thật, network/provider thật,
  thứ tự test hoặc dữ liệu còn sót. Dùng fixture/fake clock/mock tại external
  boundary và luôn cleanup resource.
- Test frontend đặt gần feature hoặc theo cấu trúc hiện hữu; test Python dùng tên
  `test_<behavior>_<condition>_<result>` khi vẫn đọc tự nhiên.
- Mỗi test kiểm chứng một behavior; không dùng sleep thật, random không seed hoặc
  assertion quá rộng. So sánh stable error code/field thay vì toàn bộ message.
- Với API, dùng `doc/content/TestCases_API.md` làm acceptance baseline; test
  wrapper, error code/status, validation, auth, ownership và edge limits.

## Verification theo phạm vi

- Frontend: `cd frontend && npm run lint && npm run build`.
- Backend: `cd app && uv run ruff check . && uv run pytest`.
- Infrastructure: validate Compose/config và health/readiness khi môi trường cho
  phép.
- Database/cache: chạy migration trên DB sạch và upgrade path phù hợp; kiểm tra
  constraint, rollback và cache-unavailable behavior.

Không tuyên bố “đã pass” nếu lệnh chưa chạy. Không sửa test chỉ để hợp code sai;
nếu contract đổi hợp lệ, cập nhật test và ghi rõ lý do.

## Documentation

- Cập nhật docs trong cùng patch khi đổi public API, business rule, schema,
  environment variable, setup command hoặc kiến trúc đáng kể.
- Không copy toàn bộ contract sang nhiều file. Link về nguồn sự thật và chỉ ghi
  ngữ cảnh chuyên biệt để tránh drift.
- `doc/ai/*.md` nên ngắn, mô tả boundary/quyết định bền vững và trỏ đến contract;
  không biến thành bản sao SRS/API spec.
- Chỉ cập nhật diagram khi topology/sequence/data relation thay đổi.
