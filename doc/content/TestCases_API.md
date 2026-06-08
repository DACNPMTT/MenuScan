# Test Cases and API Design
# AI-Powered Smart Menu Digitization and Translation System for Travelers

## 1. Mục đích

Tài liệu này mô tả các test case cho các chức năng chính của hệ thống MenuScan, bao gồm:
- Đăng nhập
- Upload ảnh menu
- OCR nhận dạng chữ
- Hiển thị Food Cards
- Xem lịch sử scan
- Tìm kiếm và lọc món ăn

Ngoài ra, tài liệu cũng bổ sung thiết kế API cho chức năng Search/Filter.

---

## 2. Test Cases

| ID | Tên test case | Mô tả | Input | Expected Output |
|---|---|---|---|---|
| TC-01 | Đăng nhập thành công | Kiểm tra người dùng đăng nhập với email và mật khẩu hợp lệ | Email: user@gmail.com, Password: 123456 | Hệ thống đăng nhập thành công và chuyển đến trang chính |
| TC-02 | Đăng nhập sai mật khẩu | Kiểm tra khi người dùng nhập sai mật khẩu | Email hợp lệ, Password sai | Hiển thị thông báo lỗi: Email hoặc mật khẩu không đúng |
| TC-03 | Đăng nhập thiếu thông tin | Kiểm tra khi người dùng bỏ trống email hoặc password | Email rỗng hoặc Password rỗng | Hiển thị thông báo yêu cầu nhập đầy đủ thông tin |
| TC-04 | Upload ảnh menu hợp lệ | Kiểm tra upload ảnh menu đúng định dạng | File JPG/PNG, dung lượng hợp lệ | Hệ thống nhận ảnh và bắt đầu xử lý OCR |
| TC-05 | Upload ảnh sai định dạng | Kiểm tra upload file không phải ảnh | File PDF/DOCX/TXT | Hiển thị thông báo lỗi: Định dạng ảnh không hợp lệ |
| TC-06 | Upload ảnh quá dung lượng | Kiểm tra upload ảnh vượt quá dung lượng cho phép | Ảnh lớn hơn giới hạn hệ thống | Hiển thị thông báo lỗi: File quá lớn |
| TC-07 | OCR thành công | Kiểm tra hệ thống nhận dạng được chữ từ ảnh menu | Ảnh menu rõ chữ | Hệ thống trả về nội dung text được nhận dạng |
| TC-08 | OCR thất bại | Kiểm tra hệ thống xử lý ảnh mờ hoặc không có chữ | Ảnh mờ, ảnh trống hoặc ảnh không chứa menu | Hiển thị thông báo: Không thể nhận dạng nội dung menu |
| TC-09 | Hiển thị Food Cards | Kiểm tra hệ thống hiển thị danh sách món ăn sau khi OCR và phân tích thành công | Text menu có tên món, giá, mô tả | Hiển thị danh sách Food Cards gồm tên món, mô tả, giá |
| TC-10 | Xem chi tiết món ăn | Kiểm tra người dùng chọn một Food Card để xem chi tiết | Click vào một Food Card | Hiển thị modal hoặc trang chi tiết món ăn |
| TC-11 | Xem lịch sử scan | Kiểm tra người dùng xem lại các lần scan trước đó | Người dùng đã đăng nhập | Hiển thị danh sách lịch sử scan |
| TC-12 | Lịch sử trống | Kiểm tra khi người dùng chưa có lịch sử scan | Người dùng chưa từng scan menu | Hiển thị thông báo: Chưa có lịch sử scan |
| TC-13 | Tìm kiếm món ăn có kết quả | Kiểm tra tìm kiếm món ăn theo từ khóa hợp lệ | Keyword: pizza | Hiển thị danh sách món ăn phù hợp |
| TC-14 | Tìm kiếm không có kết quả | Kiểm tra tìm kiếm từ khóa không tồn tại | Keyword: abcxyz | Hiển thị thông báo: Không tìm thấy kết quả |
| TC-15 | Lọc món ăn theo category | Kiểm tra lọc món ăn theo loại món | Category: Drink | Hiển thị các món thuộc loại Drink |

---

## 3. API Design cho Search/Filter

---

### 3.1 API tìm kiếm món ăn

**Endpoint**

```http
GET /api/foods/search
```

**Mô tả**

API này dùng để tìm kiếm món ăn theo từ khóa. Người dùng có thể nhập tên món ăn hoặc một phần tên món ăn. Hệ thống sẽ trả về danh sách món ăn phù hợp.

**Query Parameters**

| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
|---|---|---|---|
| keyword | String | Có | Từ khóa tìm kiếm món ăn |
| page | Number | Không | Số trang kết quả |
| limit | Number | Không | Số lượng kết quả trên mỗi trang |

**Request Example**

```http
GET /api/foods/search?keyword=pizza&page=1&limit=10
```

**Response Success**

```json
{
  "success": true,
  "message": "Search food items successfully",
  "data": [
    {
      "id": 1,
      "originalName": "Pizza Margherita",
      "translatedName": "Pizza phô mai cà chua",
      "description": "Pizza with tomato sauce and cheese",
      "price": 8.5,
      "currency": "USD",
      "category": "Main Dish"
    }
  ]
}
```

**Response Error**

```json
{
  "success": false,
  "message": "No food items found",
  "data": []
}
```

---

### 3.2 API lọc món ăn

**Endpoint**

```http
GET /api/foods/filter
```

**Mô tả**

API này dùng để lọc món ăn theo loại món, khoảng giá hoặc ngôn ngữ dịch.  
Người dùng có thể kết hợp nhiều điều kiện lọc cùng lúc.

**Query Parameters**

| Tên tham số | Kiểu dữ liệu | Bắt buộc | Mô tả |
|---|---|---|---|
| category | String | Không | Loại món ăn, ví dụ: Drink, Dessert, Main Dish |
| minPrice | Number | Không | Giá thấp nhất |
| maxPrice | Number | Không | Giá cao nhất |
| language | String | Không | Ngôn ngữ dịch mong muốn |
| page | Number | Không | Số trang kết quả |
| limit | Number | Không | Số lượng kết quả trên mỗi trang |

**Request Example**

```http
GET /api/foods/filter?category=Drink&minPrice=1&maxPrice=10&page=1&limit=10
```

**Response Success**

```json
{
  "success": true,
  "message": "Filter food items successfully",
  "data": [
    {
      "id": 2,
      "originalName": "Orange Juice",
      "translatedName": "Nước cam",
      "description": "Fresh orange juice",
      "price": 3.0,
      "currency": "USD",
      "category": "Drink"
    }
  ]
}
```

**Response Error**

```json
{
  "success": false,
  "message": "No food items match the filter",
  "data": []
}
```

---

### 3.3 Ghi chú

- API search dùng khi người dùng nhập từ khóa để tìm món ăn.
- API filter dùng khi người dùng muốn lọc theo category, giá hoặc ngôn ngữ.
- Nếu không có kết quả phù hợp, hệ thống trả về danh sách rỗng và thông báo lỗi phù hợp.