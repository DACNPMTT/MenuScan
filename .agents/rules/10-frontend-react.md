# Frontend Rules — React, TypeScript, Vite

Áp dụng cho mọi thay đổi trong `frontend/`.

## Kiến trúc

- Giữ feature-first hiện có: composition/provider/routes trong `src/app`, route
  screen trong `pages`, nghiệp vụ trong `features`, primitive dùng chung trong
  `shared`, shell trong `layouts`.
- Dùng TypeScript strict và import trực tiếp qua alias `@/`; không tạo barrel
  export chỉ để rút ngắn đường dẫn.
- Component nhỏ, một trách nhiệm. Không định nghĩa component bên trong component
  khác. Chỉ tách hook/module khi có logic hoặc consumer rõ ràng.
- Không đưa server state vào global context mặc định. Giữ state gần nơi dùng và
  chỉ thêm thư viện state/data-fetching khi task thực sự cần.

## TypeScript và naming

- Component file dùng `PascalCase.tsx`; hook dùng `useCamelCase.ts`; component,
  type/interface dùng `PascalCase`; variable/function/prop dùng `camelCase`.
- Dùng named export; props có type `<Component>Props` khi không hiển nhiên; không
  dùng `React.FC` mặc định.
- Ưu tiên literal/discriminated union; không dùng TypeScript `enum` khi union hoặc
  `as const` đủ dùng (`erasableSyntaxOnly` đang bật).
- Không dùng non-null/type assertion để né validation; dữ liệu API là `unknown`
  tới khi boundary đáng tin cậy xác nhận.
- Event handler trong component là `handle<Action>`, prop callback là
  `on<Action>`; custom hook chỉ dùng prefix `use` khi tuân Rules of Hooks.
- JSX dùng semantic element; CSS class `kebab-case`, theo BEM khi component hiện
  hữu đang dùng BEM.

## React và hiệu năng

- Song song hóa request độc lập, tránh waterfall; chỉ tải module nặng khi feature
  được dùng.
- Không dùng `useEffect` để tính derived state hoặc xử lý hành động trực tiếp của
  user; tính trong render hoặc event handler.
- Dùng functional state update khi giá trị mới phụ thuộc giá trị cũ. Không thêm
  `useMemo`/`useCallback` nếu chưa có chi phí hoặc identity requirement rõ ràng.
- Hoist constant/static JSX không phụ thuộc render. Dùng stable key từ dữ liệu,
  không dùng array index cho danh sách có thể thay đổi.

## API, UX và accessibility

- Type API bám `doc/content/api-endpoints.md`; xử lý wrapper `success/data` và
  `success/error`, không suy đoán field thiếu.
- Có loading, empty, error và retry phù hợp. Poll scan theo API, dừng ở
  `COMPLETED`/`FAILED` và cleanup timer khi unmount.
- Upload đúng một JPG/JPEG/PNG/WEBP/PDF, tối đa 10 MB và PDF tối đa 5 trang;
  client validation chỉ hỗ trợ UX, backend vẫn quyết định.
- Magic Link token phải được xóa khỏi URL bằng `history.replaceState` ngay sau khi
  đọc. Không lưu refresh token hoặc secret trong local/session storage.
- Dùng semantic HTML, label, keyboard interaction, focus state và `aria-*` khi
  semantics gốc chưa đủ. Không giao tiếp trạng thái chỉ bằng màu sắc.

## Kiểm tra

- Tối thiểu chạy trong `frontend/`: `npm run lint` và `npm run build`.
- Với logic mới có nhánh nghiệp vụ, thêm test khi test framework hiện hữu; không
  tự thêm framework test lớn nếu task không yêu cầu, hãy nêu khoảng trống.
