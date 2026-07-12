# MenuScan — Task list: Cá nhân hoá "Trợ lý chọn món"

> Định vị: **trợ lý chọn món cá nhân hoá cho khách du lịch / người kỹ tính ăn uống**.
> Quét menu → mỗi món có: dịch, giải thích, và phán đoán *hợp/không hợp với bạn + tại sao*.
>
> **Nguyên tắc ghim cứng:** sản phẩm là **trợ lý tham khảo, KHÔNG bảo hành an toàn**.
> Mọi câu chữ về dị ứng phải là *"có thể chứa X"*, không bao giờ *"an toàn cho bạn"*.

Ký hiệu công sức: **S** ≈ ≤1 ngày · **M** ≈ 2–3 ngày · **L** ≈ ≥4 ngày.
Người phụ trách là **gợi ý** — map lại theo sức từng người.

Trạng thái nền (đã có sẵn trong code, đừng làm lại):
- `users` đã có `allergies` + `dietary_preferences`.
- `food_items` đã có `allergens` + `dietary_tags` + `confidence_score`.
- `scan_sessions.user_id` đã nullable (khách không đăng nhập vẫn quét được).
- Prompt trích xuất ở `app/src/modules/menu_scan/llm_menu_parser.py` (`_build_prompt`, `_parsed_menu_schema`).

---

## Thứ tự ưu tiên (đọc trước khi nhận việc)

- **Sprint 1 — LÕI ĂN ĐIỂM:** Epic A (hồ sơ) + B (metadata món) + C (advisor) + D1/D2 (màn kết quả & chi tiết). Làm xong 4 cái này là đã có sản phẩm demo được.
- **Sprint 2 — phụ kiện:** D3 (chat), Epic E (nhóm/QR/chia bill) — **chỉ làm nếu Sprint 1 xong và còn thời gian**. Nhóm là phần ngốn công nhất, giá trị thấp nhất.
- **Xuyên suốt:** Epic F (báo cáo) chạy song song ngay từ đầu, không để dồn cuối.

---

## Epic A — Hồ sơ khẩu vị (DB + BE + FE) · *ưu tiên cao*

| ID | Track | Việc | Công | Phụ thuộc | Gợi ý |
|----|-------|------|------|-----------|-------|
| A1 | DB | Migration tạo bảng `dietary_profiles` (allergies, diet, favorites, dislikes); chuyển 2 cột từ `users` sang; thêm FK `users → profile`. Giữ tương thích dữ liệu cũ. | M | — | Tài |
| A2 | DB/Docs | Chốt **bộ taxonomy cố định**: mã dị ứng, mã chế độ ăn, danh sách nguyên liệu/vị (bò, heo, hải sản, cay, ngọt…), danh sách sở thích/ghét. Dùng chung cho cả hồ sơ lẫn `food_items`. | M | — | Hà + Tài |
| A3 | BE | API hồ sơ khẩu vị: xem/cập nhật allergies, diet, favorites, dislikes. | M | A1, A2 | Đức |
| A4 | FE | Màn hồ sơ & thiết lập: thêm mục **sở thích** + **món ghét** (chọn từ list cố định) đặt cạnh mục dị ứng đã có. | M | A2, A3 | Quang Linh |
| A5 | FE | Chuỗi hiển thị VN/EN cho các mục mới của màn hồ sơ. | S | A4 | Quang Linh |

## Epic B — Metadata món ăn cho đối chiếu (AI + DB) · *ưu tiên cao*

| ID | Track | Việc | Công | Phụ thuộc | Gợi ý |
|----|-------|------|------|-----------|-------|
| B1 | DB | Thêm trường nguyên liệu/vị vào `food_items` (bò/heo/hải sản/cay/ngọt…) để đối chiếu sở thích. Tận dụng/mở rộng `dietary_tags` theo taxonomy A2. | S | A2 | Tài |
| B2 | AI | Mở rộng prompt trích xuất (`_build_prompt`, `_parsed_menu_schema`) để LLM trả thêm nguyên liệu/vị mỗi món. **Giữ bước này profile-agnostic** (cache được). | M | B1 | Hà |
| B3 | AI | Cập nhật `output_verifier` (chống bịa) cho các trường mới. | S | B2 | Hà |
| B4 | QA/AI | Mở rộng bộ benchmark trong `doc/ocr-benchmark/` để chấm độ chính xác trường mới. | M | B2 | Tài |

## Epic C — Advisor cá nhân hoá (AI + BE) · *NGÔI SAO — ăn điểm nhất*

> Đây chính là "sửa skill AI để trả nội dung chi tiết hơn". Làm thành **bước RIÊNG**, không nhét vào prompt trích xuất.

| ID | Track | Việc | Công | Phụ thuộc | Gợi ý |
|----|-------|------|------|-----------|-------|
| C1 | AI | Module advisor mới: input = menu đã cấu trúc + hồ sơ user → output mỗi món `{verdict: nên/cân nhắc/tránh, lý do, cờ cảnh báo}`. Không chạy lại OCR. | L | A2, B2 | Hà |
| C2 | AI | Prompt + JSON schema cho advisor; câu chữ **an toàn pháp lý** (“có thể chứa…”, gợi ý “kêu ít đường”). | M | C1 | Hà |
| C3 | BE | API trả menu đã cá nhân hoá + xếp hạng cho user hiện tại. Cache: tách phần trích xuất (dùng chung) vs phần advice (theo user). | M | C1, A3 | Đức |
| C4 | BE | Logic xếp hạng: món hợp lên đầu, gắn nhãn “Gợi ý cho bạn”, giữ cảnh báo dị ứng. | S | C3 | Đức |

## Epic D — Màn kết quả & chi tiết (FE) · *ưu tiên cao (D1,D2) / vừa (D3)*

| ID | Track | Việc | Công | Phụ thuộc | Gợi ý |
|----|-------|------|------|-----------|-------|
| D1 | FE | Màn kết quả quét: từ “chỉ cảnh báo món rủi ro” nâng lên **chấm điểm + xếp hạng**; món hợp lên đầu + nhãn “Gợi ý cho bạn”; vẫn giữ cảnh báo dị ứng. | M | C4 | Quang Linh |
| D2 | FE | Màn chi tiết món: hiển thị advice per món (verdict + lý do + cờ). | M | C3 | Quang Linh |
| D3 | FE | Khung chat hỏi trợ lý trong màn chi tiết. *(Sprint 2)* | M | C1 | Quang Linh |
| D4 | FE | Chuỗi VN/EN cho các màn mới. | S | D1, D2 | Quang Linh |

## Epic E — Luồng nhóm / QR / chia bill (DB + BE + FE) · *ưu tiên THẤP, Sprint 2, có thể cắt*

| ID | Track | Việc | Công | Phụ thuộc | Gợi ý |
|----|-------|------|------|-----------|-------|
| E1 | DB | Bảng `dining_groups` (tên, mã chia sẻ, người tạo, trạng thái, hạn dùng) + `group_members` (thuộc nhóm, tên hiển thị, hồ sơ khẩu vị, khách/tài khoản). Thêm `scan_sessions.group_id`. | M | A1 | Tài |
| E2 | BE | Tạo nhóm + sinh mã/QR; tham gia bằng mã **không cần đăng nhập**; đếm số người đã điền. | L | E1 | Đức |
| E3 | FE | Màn tạo nhóm + hiện QR để chia sẻ. | M | E2 | Quang Linh |
| E4 | FE | Màn thành viên mở từ QR: điền tên + khẩu vị nhanh, không đăng nhập. | M | E2 | Quang Linh |
| E5 | FE | Màn đếm số người đã điền; nút chia tiền lấy sẵn số người từ nhóm. | M | E2, E3 | Quang Linh |
| E6 | BE | Chia bill theo đầu người (mở rộng module `billing` sẵn có). | M | E2 | Đức |

## Epic F — Báo cáo đồ án (Docs) · *chạy song song từ đầu*

| ID | Việc | Công | Gợi ý |
|----|------|------|-------|
| F1 | Cập nhật SRS + MVP contract theo định vị mới (trợ lý cá nhân hoá) — cho khớp README. | M | Hà |
| F2 | Chương Tổng quan: vấn đề, người dùng (khách du lịch/kỹ tính), **vì sao hơn Google Dịch**. | M | Đức |
| F3 | Chương Phân tích & thiết kế: use case (hồ sơ, quét, kết quả cá nhân hoá, nhóm), class diagram, **ERD cập nhật bảng mới**. | L | Tài |
| F4 | Chương Kiến trúc: pipeline AI (OCR→LLM→advisor), nhấn mạnh bộ benchmark. | M | Hà |
| F5 | Chương Cài đặt & kiểm thử: test case + kết quả benchmark OCR. | M | Tài |
| F6 | Slide + kịch bản thuyết trình + video demo. | M | Quang Linh |
| F7 | Mục đạo đức/pháp lý: disclaimer “tham khảo, không bảo hành” + chuẩn bị câu trả lời hội đồng về trách nhiệm dị ứng. | S | Hà |

---

## Chia người (tóm tắt)

- **Hà (lead):** Epic B + C (AI/advisor — lõi ăn điểm) + điều phối + F1/F4/F7.
- **Đức (backend):** A3, C3, C4, E2/E6 + F2.
- **Quang Linh (frontend):** A4/A5, D*, E3/E4/E5 + F6.
- **Tài (DB + QA):** A1/A2, B1/B4, E1 + F3/F5.

Báo cáo: mỗi người viết chương phần mình làm, Hà ráp cuối.
