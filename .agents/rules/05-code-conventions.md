# Code Conventions

Áp dụng cho mọi source code, test, migration và file cấu hình. Config tự động
gần code nhất (`eslint`, TypeScript, Ruff, formatter) có ưu tiên cao hơn ví dụ
trong tài liệu này. Không format file ngoài phạm vi task.

## Quy ước chung

- Code, identifier, filename kỹ thuật và commit-facing text dùng tiếng Anh;
  nội dung giao diện có thể theo ngôn ngữ sản phẩm. Comment giải thích **vì sao**,
  constraint hoặc trade-off, không kể lại code đang làm gì.
- Ưu tiên code dễ đọc hơn clever code: function ngắn, một mức abstraction, early
  return và tên thể hiện ý định. Tránh boolean argument khó hiểu; dùng option hoặc
  enum khi ý nghĩa tại call site không rõ.
- Không dùng magic number/string cho business rule hoặc giá trị lặp lại; đặt
  constant có tên và giữ gần module sở hữu nó. Không tạo constant cho giá trị chỉ
  dùng một lần nếu tên không tăng độ rõ ràng.
- Public function, component, API schema, service và data model phải có kiểu rõ.
  Không dùng `any`, untyped dictionary hoặc cast chỉ để làm compiler im lặng.
- Dùng immutable update mặc định. Không mutate input, shared constant hoặc dữ
  liệu cache ngoài boundary được thiết kế rõ.
- Import phải cần thiết, không unused, không wildcard. Thứ tự: standard/built-in,
  third-party, project-local; dùng type-only import khi TypeScript yêu cầu.
- Không để dead code, commented-out code, debug log, TODO mơ hồ hoặc suppression
  không lý do. TODO phải có việc cụ thể và issue/task ID nếu team đang dùng.

## Naming và file

- Tên phải dùng thuật ngữ thống nhất trong contract: `scan`, `menu`, `food_item`,
  `magic_link`, `session`; không tạo synonym như `job` hoặc `dish` cho cùng entity.
- Boolean bắt đầu bằng `is`, `has`, `can`, `should` hoặc `was`. Collection dùng
  danh từ số nhiều. Function dùng động từ; class/type/component dùng danh từ.
- Không dùng viết tắt khó hiểu. Các viết tắt chuẩn như `id`, `api`, `url`, `ocr`
  được phép nhưng phải nhất quán với convention của ngôn ngữ.
- Một file có một primary responsibility. Không tạo file `utils`, `helpers`,
  `common` hoặc `misc` chứa nhiều module không liên quan; đặt utility theo hành vi.
