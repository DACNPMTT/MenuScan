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

### UC01 - Register

#### Ten Use Case

Register

#### Mo ta

Guest tao tai khoan de co the dang nhap va su dung cac chuc nang scan, luu, quan ly menu.

#### Actor

Guest

#### Tien dieu kien

- Guest chua dang nhap.
- Guest chua co tai khoan trong he thong.

#### Hau dieu kien

- Tai khoan moi duoc tao thanh cong.
- Guest co the dang nhap bang thong tin da dang ky.

#### Luong chinh

1. Guest mo man hinh dang ky.
2. Guest nhap thong tin tai khoan.
3. Guest gui yeu cau dang ky.
4. He thong kiem tra thong tin hop le.
5. He thong tao tai khoan moi.
6. He thong thong bao dang ky thanh cong.

#### Luong thay the

- Neu Guest da co tai khoan, Guest chon chuyen sang man hinh dang nhap.

#### Luong ngoai le

- Neu email da ton tai, he thong hien thi thong bao loi.
- Neu thong tin khong hop le, he thong yeu cau Guest nhap lai.

### UC02 - Login

#### Ten Use Case

Login

#### Mo ta

User dang nhap vao he thong de truy cap cac chuc nang danh cho nguoi dung da xac thuc.

#### Actor

Guest, User

#### Tien dieu kien

- User da co tai khoan.
- User chua dang nhap vao he thong.

#### Hau dieu kien

- User dang nhap thanh cong.
- He thong chuyen User vao man hinh chinh.

#### Luong chinh

1. User mo man hinh dang nhap.
2. User nhap email va mat khau.
3. User gui yeu cau dang nhap.
4. He thong kiem tra thong tin dang nhap.
5. He thong tao phien dang nhap.
6. He thong chuyen User vao man hinh chinh.

#### Luong thay the

- Neu User quen mat khau, User chon chuc nang khoi phuc mat khau.

#### Luong ngoai le

- Neu email hoac mat khau sai, he thong hien thi thong bao loi.
- Neu tai khoan bi khoa, he thong tu choi dang nhap.

### UC03 - Upload Menu Image/PDF

#### Ten Use Case

Upload Menu Image/PDF

#### Mo ta

User tai len hinh anh hoac file PDF menu de he thong xu ly va scan noi dung.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- User co file menu hop le tren thiet bi.

#### Hau dieu kien

- File menu duoc tai len thanh cong.
- He thong san sang thuc hien scan menu.

#### Luong chinh

1. User mo chuc nang upload menu.
2. User chon hinh anh hoac file PDF menu.
3. He thong kiem tra dinh dang va dung luong file.
4. He thong tai file len may chu.
5. He thong hien thi trang thai upload thanh cong.

#### Luong thay the

- Neu User chon nhieu anh cua cung mot menu, he thong cho phep upload theo danh sach.

#### Luong ngoai le

- Neu file sai dinh dang, he thong thong bao file khong hop le.
- Neu upload that bai, he thong cho phep User thu lai.

### UC04 - Scan Menu

#### Ten Use Case

Scan Menu

#### Mo ta

User yeu cau he thong scan file menu da upload de nhan dien noi dung mon an.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- Menu image/PDF da duoc upload thanh cong.

#### Hau dieu kien

- He thong tao ket qua scan menu.
- Ket qua scan duoc chuyen sang buoc trich xuat mon an.

#### Luong chinh

1. User chon menu da upload.
2. User bat dau scan menu.
3. He thong gui file menu den bo xu ly OCR.
4. He thong nhan ket qua nhan dien van ban.
5. He thong chuyen ket qua sang chuc nang trich xuat mon an.

#### Luong thay the

- Neu he thong tu dong scan sau khi upload, User khong can bam nut scan rieng.

#### Luong ngoai le

- Neu file bi loi hoac khong doc duoc, he thong thong bao khong the scan.
- Neu OCR xu ly qua lau, he thong thong bao trang thai timeout.

### UC05 - Extract Menu Items

#### Ten Use Case

Extract Menu Items

#### Mo ta

System/OCR trich xuat ten mon, gia va thong tin lien quan tu noi dung menu da scan.

#### Actor

System/OCR

#### Tien dieu kien

- He thong da co ket qua scan/OCR tu menu.
- Noi dung OCR co du lieu van ban can phan tich.

#### Hau dieu kien

- Danh sach menu items duoc tao tu ket qua OCR.
- Du lieu duoc chuyen sang dang the menu de User xem.

#### Luong chinh

1. System/OCR nhan noi dung van ban tu ket qua scan.
2. System/OCR phan tich ten mon, gia va mo ta neu co.
3. System/OCR tao danh sach menu items.
4. He thong luu tam ket qua trich xuat.
5. He thong hien thi ket qua duoi dang cards.

#### Luong thay the

- Neu chi trich xuat duoc mot phan du lieu, he thong van tao cards cho cac mon da nhan dien.

#### Luong ngoai le

- Neu khong tim thay mon an nao, he thong thong bao khong co du lieu hop le.
- Neu gia tri gia tien khong ro rang, he thong danh dau de User chinh sua.

### UC06 - View Cards

#### Ten Use Case

View Cards

#### Mo ta

User xem danh sach mon an da duoc he thong chuyen thanh cac the menu.

#### Actor

User

#### Tien dieu kien

- Menu da duoc scan va trich xuat thanh cong.
- He thong co danh sach menu items de hien thi.

#### Hau dieu kien

- User xem duoc cac the menu.
- User co the tiep tuc chinh sua hoac luu menu.

#### Luong chinh

1. He thong hien thi danh sach menu cards.
2. User xem ten mon, gia va thong tin tung mon.
3. User kiem tra ket qua OCR tren tung card.
4. User chon thao tac tiep theo: chinh sua, luu, hoac quan ly menu.

#### Luong thay the

- Neu danh sach co nhieu mon, User co the tim kiem hoac loc card.

#### Luong ngoai le

- Neu khong co card nao, he thong hien thi trang thai rong.
- Neu du lieu card bi thieu, he thong hien thi canh bao de User chinh sua.

### UC07 - Edit Menu Item

#### Ten Use Case

Edit Menu Item

#### Mo ta

User chinh sua thong tin mon an sau khi OCR tao ra ket qua chua chinh xac hoac chua day du.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- He thong da hien thi danh sach menu cards.

#### Hau dieu kien

- Thong tin menu item duoc cap nhat.
- Card hien thi du lieu moi sau khi chinh sua.

#### Luong chinh

1. User chon mot menu card can chinh sua.
2. User thay doi ten mon, gia hoac mo ta.
3. User xac nhan luu thay doi.
4. He thong kiem tra du lieu hop le.
5. He thong cap nhat menu item.
6. He thong hien thi card da cap nhat.

#### Luong thay the

- Neu User khong muon luu thay doi, User huy thao tac va quay lai danh sach cards.

#### Luong ngoai le

- Neu gia tien khong hop le, he thong yeu cau User nhap lai.
- Neu cap nhat that bai, he thong hien thi thong bao loi.

### UC08 - Save Menu

#### Ten Use Case

Save Menu

#### Mo ta

User luu menu da scan va da chinh sua vao he thong de co the xem lai sau.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- He thong co danh sach menu items hop le.

#### Hau dieu kien

- Menu duoc luu vao tai khoan cua User.
- User co the xem menu trong danh sach menu ca nhan.

#### Luong chinh

1. User xem lai danh sach menu cards.
2. User chon luu menu.
3. User nhap ten menu neu can.
4. He thong kiem tra du lieu menu.
5. He thong luu menu vao co so du lieu.
6. He thong thong bao luu thanh cong.

#### Luong thay the

- Neu User dang sua menu da co, he thong cap nhat menu hien tai thay vi tao menu moi.

#### Luong ngoai le

- Neu menu khong co mon an hop le, he thong khong cho luu.
- Neu loi ket noi xay ra, he thong thong bao luu that bai.

### UC09 - Manage Menus

#### Ten Use Case

Manage Menus

#### Mo ta

User quan ly danh sach menu da luu, bao gom xem, tim kiem, chon menu de chinh sua hoac xoa.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- User co quyen truy cap danh sach menu ca nhan.

#### Hau dieu kien

- User xem duoc danh sach menu da luu.
- User co the tiep tuc thao tac voi tung menu.

#### Luong chinh

1. User mo man hinh quan ly menu.
2. He thong tai danh sach menu cua User.
3. He thong hien thi ten menu, ngay tao va trang thai neu co.
4. User chon mot menu de xem chi tiet.
5. He thong hien thi thong tin menu duoc chon.

#### Luong thay the

- Neu danh sach co nhieu menu, User co the tim kiem hoac loc theo ten menu.

#### Luong ngoai le

- Neu User chua co menu nao, he thong hien thi trang thai rong.
- Neu tai danh sach that bai, he thong hien thi thong bao loi.

### UC10 - Delete Menu

#### Ten Use Case

Delete Menu

#### Mo ta

User xoa menu da luu khi khong con can quan ly menu do trong he thong.

#### Actor

User

#### Tien dieu kien

- User da dang nhap.
- Menu can xoa ton tai va thuoc ve User.

#### Hau dieu kien

- Menu duoc xoa khoi danh sach menu ca nhan.
- He thong khong hien thi menu da xoa trong man hinh quan ly.

#### Luong chinh

1. User mo danh sach menu ca nhan.
2. User chon menu can xoa.
3. User chon thao tac xoa menu.
4. He thong hien thi hop thoai xac nhan.
5. User xac nhan xoa.
6. He thong xoa menu.
7. He thong cap nhat danh sach menu.

#### Luong thay the

- Neu User khong muon xoa, User huy thao tac xoa va quay lai danh sach menu.

#### Luong ngoai le

- Neu menu khong ton tai, he thong thong bao khong tim thay menu.
- Neu User khong co quyen xoa menu, he thong tu choi thao tac.
