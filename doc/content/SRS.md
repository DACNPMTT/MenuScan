# Software Requirements Specification - MenuScan

## 1. Giới thiệu

### 1.1 Mục đích tài liệu

Tài liệu SRS này mô tả các yêu cầu phần mềm cho hệ thống **AI-Powered Smart Menu Digitization and Translation System for Travelers**.  
Hệ thống hỗ trợ khách du lịch scan hoặc upload ảnh menu bằng tiếng nước ngoài, sau đó sử dụng OCR và AI để nhận diện, phân tích, dịch nội dung menu và hiển thị danh sách món ăn dưới dạng Food Cards dễ hiểu.

### 1.2 Đối tượng sử dụng

Hệ thống hướng đến các nhóm người dùng chính:

- Khách du lịch nước ngoài
- Người dùng không hiểu ngôn ngữ trên menu
- Người dùng muốn xem nhanh tên món, mô tả món, giá và bản dịch

### 1.3 Mục tiêu hệ thống

Hệ thống giúp người dùng:

- Chụp hoặc tải ảnh menu lên hệ thống
- Nhận dạng chữ trên menu bằng OCR
- Dịch tên món và mô tả món ăn sang ngôn ngữ người dùng
- Hiển thị món ăn dưới dạng Food Cards
- Xem lại lịch sử scan menu
- Tìm kiếm món ăn trong kết quả đã scan

---

## 2. Phạm vi hệ thống

### 2.1 Chức năng chính

Hệ thống bao gồm các chức năng chính sau:

- Đăng ký và đăng nhập tài khoản
- Upload hoặc chụp ảnh menu
- Kiểm tra ảnh menu hợp lệ
- OCR nhận dạng chữ trong ảnh menu
- Phân tích nội dung menu thành danh sách món ăn
- Dịch tên món và mô tả món ăn
- Hiển thị Food Cards
- Xem chi tiết món ăn
- Lưu và xem lịch sử scan
- Tìm kiếm món ăn

### 2.2 Ngoài phạm vi

Trong phiên bản đầu tiên, hệ thống chưa hỗ trợ:

- Đặt món trực tiếp tại nhà hàng
- Thanh toán online
- Đánh giá nhà hàng
- Gợi ý món ăn theo sức khỏe hoặc dị ứng
- Chat trực tiếp với nhà hàng

---

## 3. Yêu cầu chức năng

| ID | Tên yêu cầu | Mô tả | Mức ưu tiên |
|---|---|---|---|
| FR-01 | Đăng ký tài khoản | Người dùng có thể tạo tài khoản bằng email, mật khẩu và tên hiển thị. | Must |
| FR-02 | Đăng nhập | Người dùng có thể đăng nhập vào hệ thống bằng email và mật khẩu. | Must |
| FR-03 | Đăng xuất | Người dùng có thể đăng xuất khỏi hệ thống. | Must |
| FR-04 | Upload ảnh menu | Người dùng có thể upload ảnh menu từ thiết bị. | Must |
| FR-05 | Chụp ảnh menu | Người dùng có thể chụp ảnh menu trực tiếp bằng camera. | Should |
| FR-06 | Kiểm tra ảnh hợp lệ | Hệ thống kiểm tra ảnh có đúng định dạng, dung lượng và có thể xử lý được hay không. | Must |
| FR-07 | Tiền xử lý ảnh | Hệ thống có thể xử lý ảnh trước khi OCR như xoay ảnh, làm rõ chữ, cắt vùng menu. | Should |
| FR-08 | OCR nhận dạng chữ | Hệ thống sử dụng OCR để nhận dạng chữ từ ảnh menu. | Must |
| FR-09 | Xử lý lỗi OCR | Nếu OCR thất bại, hệ thống hiển thị thông báo lỗi và yêu cầu người dùng thử lại. | Must |
| FR-10 | Phân tích menu | Hệ thống phân tích nội dung OCR để tách tên món, mô tả, giá và loại món ăn. | Must |
| FR-11 | Dịch nội dung menu | Hệ thống dịch tên món và mô tả món ăn sang ngôn ngữ người dùng chọn. | Must |
| FR-12 | Hiển thị Food Cards | Hệ thống hiển thị các món ăn dưới dạng Food Cards gồm tên món, bản dịch, mô tả và giá. | Must |
| FR-13 | Xem chi tiết món ăn | Người dùng có thể chọn một Food Card để xem chi tiết món ăn. | Must |
| FR-14 | Lưu lịch sử scan | Hệ thống lưu lại lịch sử các lần scan menu của người dùng. | Should |
| FR-15 | Xem lịch sử scan | Người dùng có thể xem lại danh sách các menu đã scan trước đó. | Should |
| FR-16 | Xem chi tiết lịch sử | Người dùng có thể chọn một lịch sử scan để xem lại kết quả chi tiết. | Should |
| FR-17 | Tìm kiếm món ăn | Người dùng có thể tìm kiếm món ăn theo tên món hoặc từ khóa. | Should |
| FR-18 | Lọc món ăn | Người dùng có thể lọc món ăn theo loại món hoặc khoảng giá. | Could |
| FR-19 | Đổi ngôn ngữ dịch | Người dùng có thể chọn ngôn ngữ muốn dịch sang. | Should |
| FR-20 | Quản lý hồ sơ cá nhân | Người dùng có thể cập nhật tên hiển thị và ngôn ngữ ưu tiên. | Could |

---

## 4. Yêu cầu phi chức năng

| ID | Tên yêu cầu | Mô tả | Mức ưu tiên |
|---|---|---|---|
| NFR-01 | Hiệu năng xử lý | Hệ thống nên trả kết quả scan và dịch menu trong thời gian hợp lý, khoảng dưới 10 giây với ảnh rõ. | Must |
| NFR-02 | Tính dễ sử dụng | Giao diện phải đơn giản, dễ thao tác với khách du lịch. | Must |
| NFR-03 | Tính tương thích | Hệ thống có thể sử dụng trên trình duyệt web và thiết bị di động. | Must |
| NFR-04 | Bảo mật tài khoản | Mật khẩu người dùng phải được mã hóa trước khi lưu vào cơ sở dữ liệu. | Must |
| NFR-05 | Bảo mật dữ liệu | Ảnh menu và lịch sử scan của người dùng không được truy cập trái phép. | Must |
| NFR-06 | Độ tin cậy | Hệ thống cần xử lý được các trường hợp lỗi như ảnh mờ, ảnh sai định dạng hoặc OCR thất bại. | Must |
| NFR-07 | Khả năng mở rộng | Hệ thống có thể mở rộng thêm nhiều ngôn ngữ và nhiều loại menu khác nhau trong tương lai. | Should |
| NFR-08 | Khả năng bảo trì | Mã nguồn cần được chia thành các module rõ ràng như OCR, Translation, Menu Analysis, History. | Should |
| NFR-09 | Giao diện phản hồi | Khi hệ thống đang xử lý OCR hoặc dịch, giao diện cần hiển thị trạng thái loading. | Should |
| NFR-10 | Tính chính xác | Kết quả OCR và dịch thuật cần đủ rõ để người dùng hiểu được nội dung menu. | Must |
| NFR-11 | Khả năng phục hồi lỗi | Khi xảy ra lỗi, hệ thống cần hiển thị thông báo dễ hiểu thay vì bị treo hoặc trắng màn hình. | Must |
| NFR-12 | Tính nhất quán giao diện | Các màn hình như đăng nhập, upload, Food Cards, lịch sử cần có giao diện thống nhất. | Should |

---

## 5. Mô tả luồng nghiệp vụ chính

### 5.1 Luồng scan menu thành công

1. Người dùng mở ứng dụng.
2. Người dùng chọn chức năng Scan Menu.
3. Người dùng upload hoặc chụp ảnh menu.
4. Hệ thống kiểm tra ảnh hợp lệ.
5. Hệ thống tiền xử lý ảnh.
6. Hệ thống thực hiện OCR để nhận dạng chữ.
7. Hệ thống phân tích nội dung menu.
8. Hệ thống dịch tên món và mô tả món ăn.
9. Hệ thống tạo danh sách Food Cards.
10. Người dùng xem danh sách món ăn.
11. Người dùng chọn món để xem chi tiết.

### 5.2 Luồng lỗi ảnh không hợp lệ

1. Người dùng upload ảnh menu.
2. Hệ thống kiểm tra ảnh.
3. Nếu ảnh sai định dạng, quá dung lượng hoặc không đọc được, hệ thống hiển thị thông báo lỗi.
4. Người dùng upload hoặc chụp lại ảnh khác.

### 5.3 Luồng lỗi OCR thất bại

1. Người dùng upload ảnh menu hợp lệ.
2. Hệ thống thực hiện OCR.
3. Nếu OCR không nhận dạng được chữ, hệ thống hiển thị thông báo lỗi.
4. Người dùng được yêu cầu thử lại với ảnh rõ hơn.

---

## 6. Yêu cầu dữ liệu

### 6.1 User

Thông tin người dùng bao gồm:

- id
- fullName
- email
- passwordHash
- preferredLanguage
- role
- createdAt

### 6.2 ScanSession

Thông tin phiên scan bao gồm:

- id
- userId
- imageUrl
- originalText
- targetLanguage
- status
- createdAt
- completedAt

### 6.3 Menu

Thông tin menu bao gồm:

- id
- scanSessionId
- title
- sourceLanguage
- targetLanguage
- createdAt

### 6.4 FoodItem

Thông tin món ăn bao gồm:

- id
- menuId
- originalName
- translatedName
- originalDescription
- translatedDescription
- price
- currency
- category
- imageUrl

---

## 7. Quy tắc nghiệp vụ

| ID | Quy tắc | Mô tả |
|---|---|---|
| BR-01 | Kiểm tra định dạng ảnh | Hệ thống chỉ chấp nhận các định dạng ảnh phổ biến như JPG, PNG, JPEG. |
| BR-02 | Kiểm tra dung lượng ảnh | Ảnh upload không được vượt quá giới hạn dung lượng hệ thống quy định. |
| BR-03 | Xử lý OCR thất bại | Nếu OCR thất bại, hệ thống không tạo Food Cards và yêu cầu người dùng thử lại. |
| BR-04 | Lưu lịch sử | Chỉ người dùng đã đăng nhập mới có thể lưu và xem lịch sử scan. |
| BR-05 | Hiển thị Food Cards | Chỉ hiển thị Food Cards khi hệ thống phân tích được ít nhất một món ăn. |

---

## 8. Kết luận

Tài liệu SRS này mô tả các yêu cầu chính của hệ thống AI-Powered Smart Menu Digitization and Translation System for Travelers.  
Hệ thống tập trung vào việc hỗ trợ khách du lịch hiểu menu nước ngoài thông qua OCR, AI Translation và giao diện Food Cards trực quan.  
Các yêu cầu được phân loại theo mức độ ưu tiên Must, Should và Could để hỗ trợ nhóm phát triển xác định phạm vi triển khai phù hợp trong từng giai đoạn.