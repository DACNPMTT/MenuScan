# 📟 MENU SCAN — Retro Digitizer Terminal

```text
███╗   ███╗███████╗███╗   ██╗██╗   ██╗███████╗ ██████╗ ██████╗███╗   ██╗
████╗ ████║██╔════╝████╗  ██║██║   ██║██╔════╝██╔════╝██╔════╝████╗  ██║
██╔████╔██║█████╗  ██╔██╗ ██║██║   ██║███████╗██║     ███████╗██╔██╗ ██║
██║╚██╔╝██║██╔══╝  ██║╚██╗██║██║   ██║╚════██║██║     ██╔═══██║██║╚██╗██║
██║ ╚═╝ ██║███████╗██║ ╚████║╚██████╔╝███████║╚██████╗██║   ██║██║ ╚████║
╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝   ╚═╝╚═╝  ╚═══╝
```

> **[HỆ THỐNG SỐ HÓA MENU CỔ ĐIỂN]**
>
> 💡 **Bài toán:** Giải quyết triệt để vấn đề menu nhà hàng khó đọc, chữ mờ, phông chữ rối mắt hoặc bố cục không thân thiện.
> 
> 🛠️ **Giải pháp:** Quét menu hình ảnh ➔ Chuyển qua mô hình xử lý ➔ Trích xuất văn bản thô (Raw Text) ➔ Phân tích qua OCR Model ➔ Trả về cấu trúc JSON ➔ Hiển thị trực quan dưới dạng Thẻ Món Ăn (Food Cards) tương tác.

---

## ⚡ BẢN ĐỒ DÒNG DỮ LIỆU (DATA FLOW)

```text
  [ 📷 Scan Menu ]
         │
         ▼
  [ 🧠 Simple Model ]  ───(Trích xuất)───>  [ 📝 Raw Text ]
                                                  │
                                                  ▼
  [ 🎴 Food Cards ]   <───(JSON Data)───   [ 🔍 OCR Model ]
```

---

## 🏗️ CẤU TRÚC HỆ THỐNG (4 MODULES)

Hệ thống được chia nhỏ thành 4 mô-đun cốt lõi độc lập và dễ mở rộng:

### 1. 📺 Front-End (FE) — `core/FE`
*Xây dựng giao diện retro hoài cổ và mượt mà bằng **React**.*
- 📁 **Upload Ảnh:** Giao diện kéo-thả ảnh menu trực quan.
- 🖼️ **Hiển thị:** Trình xem ảnh menu động tích hợp zoom.
- 🎴 **Food Card:** Thẻ món ăn hiển thị giá tiền, hình ảnh minh họa, và mô tả.
- 🔍 **Xem Chi Tiết:** Modal popup xem chi tiết nguyên liệu, dinh dưỡng hoặc ghi chú món ăn.

### 2. 🔌 Back-End (BE) — `core/BE`
*API Gateway hiệu năng cao xây dựng trên nền tảng **Python + FastAPI**.*
- 🔑 **Authentication:** Xác thực và phân quyền người dùng (JWT).
- 📤 **Upload Image:** Tiếp nhận, tối ưu hóa và lưu trữ tệp ảnh menu.
- 🗃️ **Menu & Card Management:** Quản lý cơ sở dữ liệu menu, danh mục món ăn và thẻ.
- 🌐 **API Endpoints:** Cung cấp RESTful API đầy đủ cho Frontend truy vấn.

### 3. 🧠 AI & OCR Skill — `core/SKILL`
*Bộ não trích xuất và chuẩn hóa dữ liệu hình ảnh.*
- 🖼️ **Image -> Text:** Chuyển đổi dữ liệu ảnh thành văn bản thô bằng OCR Model.
- ⚙️ **Raw OCR:** Trực quan hóa dữ liệu thô, loại bỏ nhiễu chữ.
- 📦 **JSON Formatting:** Phân tích cú pháp văn bản thô thành cấu trúc dữ liệu JSON chuẩn.

### 4. 💾 Database (DB) — `core/DB`
*Hệ quản trị cơ sở dữ liệu mạnh mẽ.*
- 🐘 **PostgreSQL:** Lưu trữ thông tin tài khoản, danh sách menu đã quét, chi tiết các thẻ món ăn (food cards), và lịch sử quét của người dùng.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

| Công nghệ | Vai trò | Trạng thái |
| :--- | :--- | :--- |
| **Python 3.10+** | Ngôn ngữ phát triển Back-end & AI/OCR | 🟢 Active |
| **FastAPI** | Framework xây dựng RESTful API tốc độ cao | 🟢 Active |
| **React** | Thư viện xây dựng giao diện người dùng | 🟢 Active |
| **PostgreSQL** | Hệ quản trị cơ sở dữ liệu quan hệ lưu trữ dữ liệu | 🟢 Active |

---

```text
+-------------------------------------------------------------+
|  [!] HƯỚNG DẪN BẮT ĐẦU NHANH                                |
|                                                             |
|  1. Di chuyển vào thư mục core/ để phát triển từng mô-đun:  |
|     $ cd core/FE && npm install                             |
|     $ cd core/BE && pip install -r requirements.txt         |
|                                                             |
|  2. Khởi tạo cơ sở dữ liệu PostgreSQL ở core/DB/             |
+-------------------------------------------------------------+
```
