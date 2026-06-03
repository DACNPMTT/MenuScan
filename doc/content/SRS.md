# Software Requirements Specification - MenuScan

## 1. Gioi thieu

MenuScan la he thong ho tro quet, nhan dien va quan ly thuc don tu hinh anh/PDF, giup nguoi dung so hoa menu va tra cuu thong tin mon an.

## 2. Actors

- Guest: Nguoi dung chua dang nhap.
- User: Nguoi dung da dang nhap.
- Admin: Quan tri vien he thong.

## 3. Chuc nang chinh

### 3.1 Dang ky / dang nhap

Actor: Guest, User
Muc do: Bat buoc MVP

### 3.2 Upload anh menu

Actor: User
Muc do: Bat buoc MVP

### 3.3 Nhan dien noi dung menu bang OCR

Actor: User
Muc do: Bat buoc MVP

### 3.4 Xem ket qua nhan dien menu

Actor: User
Muc do: Bat buoc MVP

### 3.5 Chinh sua thong tin mon an sau OCR

Actor: User
Muc do: Bat buoc MVP

### 3.6 Luu menu da so hoa

Actor: User
Muc do: Bat buoc MVP

### 3.7 Quan ly danh sach menu ca nhan

Actor: User
Muc do: Bat buoc MVP

### 3.8 Quan ly nguoi dung

Actor: Admin
Muc do: Tuy chon / Sau MVP

## 4. Phan loai chuc nang

| Chuc nang | Actor | Bat buoc MVP | Ghi chu |
|---|---|---|---|
| Dang ky / dang nhap | Guest/User | Co | Xac thuc tai khoan |
| Upload anh menu | User | Co | Nhan anh/PDF |
| OCR menu | User | Co | Trich xuat ten mon, gia |
| Xem ket qua OCR | User | Co | Hien thi du lieu da nhan dien |
| Chinh sua mon an | User | Co | Sua loi OCR |
| Luu menu | User | Co | Luu vao he thong |
| Quan ly menu ca nhan | User | Co | Xem/sua/xoa menu |
| Quan ly nguoi dung | Admin | Khong | Co the lam sau |

## 5. Yeu cau phi chuc nang

- Giao dien de su dung.
- He thong xu ly anh menu trong thoi gian hop ly.
- Du lieu nguoi dung can duoc bao mat.
- Ket qua OCR co the duoc nguoi dung chinh sua.
- He thong hoat dong on dinh tren trinh duyet web.

## 6. Use Case Specification

Mo ta ngan gon cac Use Case chinh trong MVP. Moi Use Case co actor, tien dieu kien, hau dieu kien, luong chinh, luong thay the va luong ngoai le.

### UC01 - Register

- Ten: Register
- Actor: Guest
- Mo ta: Guest tao tai khoan moi.
- Tien dieu kien: Guest chua dang nhap.
- Hau dieu kien: Tai khoan duoc tao thanh cong.
- Luong chinh: Guest nhap thong tin -> he thong kiem tra -> tao tai khoan.
- Luong thay the: Guest chuyen sang Login neu da co tai khoan.
- Luong ngoai le: Email da ton tai hoac thong tin khong hop le.

### UC02 - Login

- Ten: Login
- Actor: Guest, User
- Mo ta: User dang nhap de su dung he thong.
- Tien dieu kien: User da co tai khoan.
- Hau dieu kien: User dang nhap thanh cong.
- Luong chinh: User nhap email/mat khau -> he thong kiem tra -> vao man hinh chinh.
- Luong thay the: User chon khoi phuc mat khau neu quen mat khau.
- Luong ngoai le: Email/mat khau sai hoac tai khoan bi khoa.

### UC03 - Upload Menu Image/PDF

- Ten: Upload Menu Image/PDF
- Actor: User
- Mo ta: User tai anh hoac PDF menu len he thong.
- Tien dieu kien: User da dang nhap va co file menu hop le.
- Hau dieu kien: File menu duoc upload thanh cong.
- Luong chinh: User chon file -> he thong kiem tra file -> upload thanh cong.
- Luong thay the: User upload nhieu anh cho cung mot menu.
- Luong ngoai le: File sai dinh dang, qua dung luong hoac upload that bai.

### UC04 - Scan Menu

- Ten: Scan Menu
- Actor: User
- Mo ta: He thong scan file menu da upload.
- Tien dieu kien: Menu da duoc upload.
- Hau dieu kien: He thong co ket qua OCR de xu ly tiep.
- Luong chinh: User bat dau scan -> he thong gui file den OCR -> nhan ket qua.
- Luong thay the: He thong tu dong scan ngay sau khi upload.
- Luong ngoai le: File khong doc duoc hoac OCR xu ly qua lau.

### UC05 - Extract Menu Items

- Ten: Extract Menu Items
- Actor: System/OCR
- Mo ta: Trich xuat ten mon, gia va thong tin lien quan tu ket qua OCR.
- Tien dieu kien: Da co ket qua scan/OCR.
- Hau dieu kien: Danh sach menu items duoc tao.
- Luong chinh: OCR doc noi dung -> phan tich mon/gia -> tao danh sach items.
- Luong thay the: Chi trich xuat duoc mot phan du lieu va danh dau can sua.
- Luong ngoai le: Khong tim thay mon an hop le.

### UC06 - View Cards

- Ten: View Cards
- Actor: User
- Mo ta: User xem cac mon an duoi dang the menu.
- Tien dieu kien: Da co danh sach menu items.
- Hau dieu kien: User co the chinh sua hoac luu menu.
- Luong chinh: He thong hien thi cards -> User xem ten mon, gia, mo ta.
- Luong thay the: User tim kiem hoac loc card neu danh sach dai.
- Luong ngoai le: Khong co card hoac card thieu du lieu.

### UC07 - Edit Menu Item

- Ten: Edit Menu Item
- Actor: User
- Mo ta: User sua thong tin mon an khi OCR nhan sai.
- Tien dieu kien: He thong da hien thi menu cards.
- Hau dieu kien: Menu item duoc cap nhat.
- Luong chinh: User chon card -> sua ten/gia/mo ta -> luu thay doi.
- Luong thay the: User huy thao tac va giu du lieu cu.
- Luong ngoai le: Gia tien khong hop le hoac cap nhat that bai.

### UC08 - Save Menu

- Ten: Save Menu
- Actor: User
- Mo ta: User luu menu da scan vao tai khoan.
- Tien dieu kien: Co danh sach menu items hop le.
- Hau dieu kien: Menu duoc luu va co the xem lai.
- Luong chinh: User chon Save -> he thong kiem tra -> luu menu.
- Luong thay the: Neu menu da ton tai, he thong cap nhat menu hien tai.
- Luong ngoai le: Menu rong hoac loi ket noi khi luu.

### UC09 - Manage Menus

- Ten: Manage Menus
- Actor: User
- Mo ta: User xem va quan ly cac menu da luu.
- Tien dieu kien: User da dang nhap.
- Hau dieu kien: Danh sach menu ca nhan duoc hien thi.
- Luong chinh: User mo danh sach -> he thong tai menu -> User chon menu can xem.
- Luong thay the: User tim kiem hoac loc menu.
- Luong ngoai le: Chua co menu nao hoac tai danh sach that bai.

### UC10 - Delete Menu

- Ten: Delete Menu
- Actor: User
- Mo ta: User xoa menu khong con can dung.
- Tien dieu kien: Menu ton tai va thuoc ve User.
- Hau dieu kien: Menu bi xoa khoi danh sach ca nhan.
- Luong chinh: User chon menu -> chon Delete -> xac nhan -> he thong xoa menu.
- Luong thay the: User huy thao tac xoa.
- Luong ngoai le: Menu khong ton tai hoac User khong co quyen xoa.
