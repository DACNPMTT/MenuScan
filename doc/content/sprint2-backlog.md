# Sprint 2 — Backlog Ưu Tiên

> Tài liệu này ghi lại các user story được ưu tiên đưa vào Sprint 2, dựa trên phản hồi sau Sprint 1.
> Tham chiếu board: https://github.com/orgs/DACNPMTT/projects/1

---

## S2-01 · Chọn ngôn ngữ dịch trước khi quét

**Loại:** Feature — Frontend + Backend
**Ưu tiên:** High
**Phụ thuộc:** S1-23 (scan API)

### Mô tả
Người dùng hiện không có cách nào chỉ định ngôn ngữ đích trước khi gửi file lên. Backend có field `target_language` trong `POST /api/v1/scans` nhưng frontend chưa expose.

### Mục tiêu
- Hiển thị dropdown / pill selector danh sách ngôn ngữ thông dụng trên trang upload.
- Gửi `target_language` vào body/form khi tạo scan.
- Trang kết quả hiển thị badge "Dịch sang: Tiếng Việt / English / ..." phản ánh ngôn ngữ thực tế Gemini đã dùng.

### Danh sách ngôn ngữ tối thiểu
| Code | Hiển thị |
|------|----------|
| `vi` | Tiếng Việt |
| `en` | English |
| `zh` | 中文 |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `fr` | Français |
| `th` | ภาษาไทย |

### Tiêu chí hoàn thành
- [ ] Selector hiển thị trên trang /app/scan trước khi bấm "Bắt đầu quét".
- [ ] Giá trị mặc định là `vi` (Tiếng Việt).
- [ ] `target_language` được gửi lên backend khi tạo scan.
- [ ] Trang kết quả hiển thị đúng ngôn ngữ đích đã chọn.
- [ ] Backend validate `target_language` — trả 400 nếu không hợp lệ.

---

## S2-02 · Hiển thị ngôn ngữ phát hiện và ngôn ngữ dịch trên trang kết quả

**Loại:** Feature — Frontend
**Ưu tiên:** High
**Phụ thuộc:** S2-01

### Mô tả
Sau khi scan hoàn tất, người dùng không biết menu gốc được viết bằng ngôn ngữ gì và đã dịch sang ngôn ngữ gì. Thông tin `detected_language` và `target_language` đã có trong response API nhưng chưa được render.

### Tiêu chí hoàn thành
- [ ] Badge "Phát hiện: [Ngôn ngữ gốc]" và "Dịch sang: [Ngôn ngữ đích]" hiển thị trong header kết quả.
- [ ] Code ISO (vi, en, ...) được chuyển thành tên đầy đủ (Tiếng Việt, English, ...).
- [ ] Ẩn badge phát hiện khi detected_language = null.

---

## S2-03 · Card món ăn với mô tả đầy đủ

**Loại:** Feature — Frontend
**Ưu tiên:** High
**Phụ thuộc:** S1-23 (result API)

### Mô tả
Hiện tại trang kết quả chỉ hiển thị danh sách phẳng tên món + giá. Cần thay bằng grid card trực quan, đầy đủ thông tin: tên gốc, tên dịch, mô tả, giá, danh mục.

### Cấu trúc card
- Badge category (nếu có)
- Tên gốc + Giá (bold)
- Tên dịch (nếu khác tên gốc)
- Mô tả gốc / mô tả dịch (nếu có)

### Tiêu chí hoàn thành
- [ ] Mỗi món là 1 card riêng biệt, không phải list row.
- [ ] Hiển thị: original_name, translated_name, price+currency, original_description, translated_description, category badge.
- [ ] Ẩn phần mô tả nếu cả hai đều null.
- [ ] Grid responsive: 1 cột mobile, 2 cột tablet, 3 cột desktop (>=1024px).
- [ ] Giữ nguyên empty state khi items = [].

---

## S2-Bonus-01 · Nhóm món theo danh mục

**Loại:** Feature — Frontend
**Ưu tiên:** Medium-High
**Phụ thuộc:** S2-03

### Mô tả
Khi Gemini trả về `category` cho từng món (ví dụ: Phở, Bún, Đồ thêm, Nước uống...), các card hiện tại vẫn đổ phẳng theo thứ tự `sort_order`. Với menu nhiều món (20–50+), việc cuộn qua danh sách phẳng rất khó theo dõi. Task này nhóm card theo từng danh mục, hiển thị header tên nhóm rõ ràng giữa các phần.

### Mục tiêu
- Group các `MenuItem` theo field `category`; các món không có category gom vào nhóm "Khác".
- Mỗi nhóm có sticky section header với tên danh mục và số lượng món.
- Thứ tự nhóm theo `sort_order` nhỏ nhất trong nhóm.
- Nếu tất cả món đều không có `category`, không hiện header, giữ nguyên grid.

### Tiêu chí hoàn thành
- [ ] Các món được nhóm theo category; có section header cho mỗi nhóm.
- [ ] Nhóm "Khác" xuất hiện cuối cùng nếu có món không có category.
- [ ] Khi chỉ có 1 nhóm hoặc tất cả null category, không render header.
- [ ] Layout grid bên trong mỗi nhóm giữ nguyên responsive từ S2-03.

---

## S2-Bonus-02 · Lưu menu và trang lịch sử quét

**Loại:** Feature — Frontend + Backend
**Ưu tiên:** High
**Phụ thuộc:** S1-23, S2-03

### Mô tả
Trang kết quả scan hiện không có nút Lưu menu. Field `is_saved` đã có trong response API (`GET /api/v1/scans/{id}/result`) nhưng chưa có endpoint để toggle. Người dùng scan xong không thể lưu lại để xem sau. Dashboard hiện tại cũng trống hoàn toàn — chưa có danh sách lịch sử scan.

### Mục tiêu
- Thêm nút **"Lưu menu"** trên trang kết quả; gọi `PATCH /api/v1/scans/{id}` hoặc endpoint lưu phù hợp để set `is_saved = true`.
- Dashboard hiển thị danh sách các scan đã thực hiện: thumbnail ảnh gốc, tên file, số món, trạng thái, thời gian.
- Cho phép xem lại scan cũ từ Dashboard bằng cách click vào item.

### Tiêu chí hoàn thành
- [ ] Nút "Lưu menu" hiển thị trên trang kết quả; toggle saved state, cập nhật icon.
- [ ] `GET /api/v1/scans` (list) trả về danh sách scan của user theo thứ tự mới nhất trước.
- [ ] Dashboard render danh sách scan: thumbnail, tên file, số món, trạng thái badge, thời gian quét.
- [ ] Click vào item lịch sử điều hướng đến `/app/scans/{id}`.
- [ ] Phân trang hoặc infinite scroll nếu danh sách dài.

---

## S2-Bonus-03 · Hiển thị độ tin cậy và highlight món nghi ngờ

**Loại:** Feature — Frontend
**Ưu tiên:** Medium
**Phụ thuộc:** S2-03

### Mô tả
Mỗi `MenuItem` đã có `confidence_score` (0.0–1.0) từ Gemini, phản ánh mức độ chắc chắn khi trích xuất. Hiện tại con số này không hiển thị ở đâu. Người dùng không biết món nào có thể bị OCR nhận sai, tên sai hoặc giá không đúng.

### Mục tiêu
- Hiển thị icon cảnh báo nhỏ và tooltip "Có thể không chính xác — vui lòng kiểm tra lại" trên các card có `confidence_score < 0.65`.
- Border/background card màu vàng nhạt cho món nghi ngờ thay vì màu mặc định.
- Không hiển thị số confidence thô; chỉ dùng 2 trạng thái: bình thường và cần kiểm tra.

### Tiêu chí hoàn thành
- [ ] Card với `confidence_score < 0.65` có visual indicator (border vàng + icon ⚠).
- [ ] Tooltip hoặc label giải thích tại sao bị đánh dấu.
- [ ] Card `confidence_score >= 0.65` hoặc `null` hiển thị bình thường, không có indicator.

---

## S2-Bonus-04 · Chỉnh sửa kết quả OCR inline

**Loại:** Feature — Frontend + Backend
**Ưu tiên:** Medium-High
**Phụ thuộc:** S2-03, S2-Bonus-02

### Mô tả
Khi menu bị mờ, font lạ hoặc OCR nhận sai, người dùng không có cách sửa. Đây là task đã nằm trong `mvp-contract.md` cho Sprint 2. Cần cho phép chỉnh sửa `original_name`, `price`, `category`, `original_description` ngay trên card kết quả mà không cần rời trang.

### Mục tiêu
- Mỗi card có nút Edit (bút chì) để bật chế độ chỉnh sửa inline.
- Khi Edit: các field chuyển thành input/textarea có thể gõ.
- Nút Lưu (✓) và Hủy (✗) xuất hiện; Lưu gọi `PATCH /api/v1/menus/{menu_id}/items/{item_id}`.
- Sau khi lưu thành công, card cập nhật ngay mà không reload trang.

### Tiêu chí hoàn thành
- [ ] Nút Edit xuất hiện khi hover hoặc focus vào card (không chiếm không gian khi ẩn).
- [ ] Chỉnh sửa được: original_name, price, category, original_description.
- [ ] API `PATCH /api/v1/menus/{menu_id}/items/{item_id}` nhận và lưu thay đổi.
- [ ] Validation: tên không được rỗng; price phải là số hợp lệ hoặc null.
- [ ] Optimistic update — card cập nhật ngay, rollback nếu API trả lỗi.

---

## S2-Bonus-05 · Xuất kết quả (Export CSV / JSON)

**Loại:** Feature — Frontend
**Ưu tiên:** Medium
**Phụ thuộc:** S2-03

### Mô tả
Nhà hàng hoặc nhân viên thường muốn đưa dữ liệu món ăn vào hệ thống quản lý (POS, Excel, Google Sheets). Hiện tại không có cách nào tải kết quả scan xuống. Task này thêm chức năng export trực tiếp từ trang kết quả, không cần API mới (client-side export từ dữ liệu đã load).

### Mục tiêu
- Nút **"Xuất file"** trên trang kết quả với 2 tuỳ chọn: CSV và JSON.
- CSV gồm các cột: STT, Tên gốc, Tên dịch, Mô tả, Giá, Tiền tệ, Danh mục.
- JSON export nguyên cấu trúc `items[]` từ API response.
- Export được thực hiện hoàn toàn client-side (không cần gọi thêm API).

### Tiêu chí hoàn thành
- [ ] Nút "Xuất file" hiển thị trên trang kết quả khi `items.length > 0`.
- [ ] Dropdown chọn định dạng: CSV hoặc JSON.
- [ ] File CSV đúng encoding UTF-8 BOM (để Excel đọc được tiếng Việt).
- [ ] Tên file mặc định: `menuscan-{tên_file_gốc}-{ngày}.csv`.
- [ ] Không có API call thêm; toàn bộ xử lý trên browser.

---

## Tóm tắt toàn bộ Sprint 2

| ID | Tên | Ưu tiên | Loại |
|----|-----|---------|------|
| S2-01 | Chọn ngôn ngữ dịch trước khi quét | 🔴 High | FE + BE |
| S2-02 | Badge ngôn ngữ phát hiện và dịch trên trang kết quả | 🔴 High | FE |
| S2-03 | Card món ăn với mô tả đầy đủ | 🔴 High | FE |
| S2-Bonus-01 | Nhóm món theo danh mục | 🟠 Med-High | FE |
| S2-Bonus-02 | Lưu menu và trang lịch sử quét | 🔴 High | FE + BE |
| S2-Bonus-03 | Hiển thị độ tin cậy, highlight món nghi ngờ | 🟡 Medium | FE |
| S2-Bonus-04 | Chỉnh sửa kết quả OCR inline | 🟠 Med-High | FE + BE |
| S2-Bonus-05 | Xuất kết quả CSV / JSON | 🟡 Medium | FE |
