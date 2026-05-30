# 📋 BẢNG PHÂN CHIA NHIỆM VỤ DỰ ÁN (TASK SHEET)

> **Dự án:** MenuScan — Số hóa Menu nhà hàng
> **Phiên bản:** v1.0.0 (Giai đoạn khởi tạo)

---

## 📊 BẢNG TỔNG HỢP PHÂN CHIA CÔNG VIỆC

| Mã Task | Phân Hệ | Tên Nhiệm Vụ | Mô Tả Chi Tiết | Phụ Trách (Vai Trò) | Trạng Thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FE-01** | Frontend | **Khởi tạo & Setup FE** | Tạo khung dự án React (Vite), cài đặt các thư viện bổ trợ và cấu hình giao diện mang phong cách Retro. | FE Developer | ⬜ Chưa bắt đầu |
| **FE-02** | Frontend | **Module Tải Ảnh** | Xây dựng giao diện kéo-thả tải ảnh Menu lên, kiểm tra định dạng và kích thước ảnh. | FE Developer | ⬜ Chưa bắt đầu |
| **FE-03** | Frontend | **Module Hiển Thị Menu** | Giao diện hiển thị ảnh Menu gốc đã tải, hỗ trợ các thao tác phóng to/thu nhỏ (Zoom/Pan). | FE Developer | ⬜ Chưa bắt đầu |
| **FE-04** | Frontend | **Giao diện Food Cards** | Thiết kế các thẻ món ăn hiển thị tên món, giá, hình ảnh minh họa trích xuất từ JSON. | FE Developer | ⬜ Chưa bắt đầu |
| **FE-05** | Frontend | **Modal Chi Tiết Món Ăn** | Giao diện xem chi tiết món ăn (nguyên liệu, mô tả chi tiết) khi người dùng nhấp vào thẻ. | FE Developer | ⬜ Chưa bắt đầu |
| **BE-01** | Backend | **Khởi tạo & Setup BE** | Cấu hình FastAPI, thiết lập cấu trúc thư mục tiêu chuẩn, quản lý môi trường (`.env`). | BE Developer | ⬜ Chưa bắt đầu |
| **BE-02** | Backend | **Module Xác Thực (Auth)** | Xây dựng API đăng ký, đăng nhập và tích hợp mã hóa JWT để bảo mật các API khác. | BE Developer | ⬜ Chưa bắt đầu |
| **BE-03** | Backend | **API Tải Ảnh & Lưu Trữ** | API tiếp nhận ảnh từ FE, xử lý tối ưu dung lượng ảnh và lưu trữ vào thư mục lưu trữ tạm thời/cloud. | BE Developer | ⬜ Chưa bắt đầu |
| **BE-04** | Backend | **API Quản Lý Menu & Card** | Thiết lập các API CRUD để truy vấn danh sách menu đã quét, danh sách món ăn từ DB. | BE Developer | ⬜ Chưa bắt đầu |
| **BE-05** | Backend | **Tích hợp cổng OCR (Gateway)** | Cầu nối gọi sang module OCR/SKILL để đẩy ảnh qua và tiếp nhận dữ liệu JSON trả về. | BE Developer | ⬜ Chưa bắt đầu |
| **OCR-01** | OCR / Skill | **Tích hợp OCR Core** | Cài đặt và cấu hình thư viện/mô hình OCR (EasyOCR, Tesseract hoặc PaddleOCR) để đọc chữ từ ảnh. | AI Engineer | ⬜ Chưa bắt đầu |
| **OCR-02** | OCR / Skill | **Xử Lý Văn Bản Thô** | Làm sạch văn bản thô sau khi OCR (loại bỏ ký tự rác, ghép dòng bị đứt quãng). | AI Engineer | ⬜ Chưa bắt đầu |
| **OCR-03** | OCR / Skill | **Trích Xuất JSON** | Áp dụng mô hình ngôn ngữ đơn giản / luật trích xuất để chuyển văn bản thô thành định dạng JSON chuẩn. | AI Engineer | ⬜ Chưa bắt đầu |
| **DB-01** | Database | **Thiết Kế Schema DB** | Thiết kế cơ sở dữ liệu trên PostgreSQL với các bảng: `users`, `menus`, `food_items`, `sessions`. | Database Admin / BE | ⬜ Chưa bắt đầu |
| **DB-02** | Database | **Kết Nối & Migration** | Cấu hình SQLAlchemy/Alembic kết nối FastAPI với PostgreSQL, viết các file migration. | Database Admin / BE | ⬜ Chưa bắt đầu |

---

## 📅 LỘ TRÌNH TRIỂN KHAI (ROADMAP)

### Giai đoạn 1: Chuẩn bị & Hạ tầng 🛠️
- Thiết kế Database Schema (`DB-01`).
- Thiết lập khung dự án cho Frontend (`FE-01`) và Backend (`BE-01`).
- Cài đặt cốt lõi module OCR (`OCR-01`).

### Giai đoạn 2: Phát triển tính năng lõi (Core Flow) 🧠
- Hoàn thiện API Upload Ảnh (`BE-03`) và giao diện Upload (`FE-02`).
- Phát triển pipeline OCR chuyển ảnh thành text (`OCR-02`) và chuyển thành JSON (`OCR-03`).
- Tích hợp cổng kết nối BE với OCR (`BE-05`).

### Giai đoạn 3: Hoàn thiện & Giao diện người dùng 🎨
- Xây dựng giao diện hiển thị Menu (`FE-03`) và Food Cards (`FE-04`, `FE-05`).
- Xây dựng module đăng nhập bảo mật (`BE-02`).
- Kết nối đồng bộ dữ liệu giữa Frontend, Backend và Database.

---

*Lưu ý: Bảng phân chia công việc này có thể được cập nhật liên tục dựa trên tiến độ thực tế của dự án.*
