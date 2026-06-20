# MenuScan - Luồng làm việc và nghiệp vụ dành cho cả nhóm

> Tài liệu dùng để phổ biến nghiệp vụ, thứ tự triển khai và cách phối hợp trong
> Sprint 1–2. Nếu có nội dung khác với
> [MVP Contract](content/mvp-contract.md), MVP Contract là nguồn ưu tiên.

## 1. Nhóm đang xây dựng sản phẩm gì?

MenuScan giúp người dùng chuyển ảnh hoặc PDF thực đơn thành dữ liệu món ăn có
cấu trúc. Người dùng có thể đối chiếu kết quả với file gốc, sửa dữ liệu nhận
diện chưa chính xác, chọn món, thêm các khoản phí và chia hóa đơn theo đầu
người.

Luồng sản phẩm hoàn chỉnh:

```text
Guest
  -> Landing Page
  -> Nhập email
  -> Nhận và mở Magic Link
  -> Dashboard
  -> Upload/chụp menu
  -> OCR + phân tích + dịch
  -> Xem file gốc và kết quả
  -> Sửa/xác nhận/lưu menu
  -> Chọn món
  -> Thêm phí, thuế hoặc giảm giá
  -> Chia bill
  -> Digital Receipt
  -> Xem lại lịch sử
```

## 2. Các quyết định nghiệp vụ cả nhóm phải nhớ

### Xác thực

- MVP chỉ đăng nhập bằng Magic Link.
- Không có password, Register riêng, Forgot Password hoặc Reset Password.
- Email mới được tự động tạo user sau khi Magic Link được xác minh.
- Magic Link sống 15 phút, chỉ dùng một lần và resend sau tối thiểu 60 giây.
- Access token sống 15 phút.
- Refresh token sống 30 ngày, lưu trong cookie `HttpOnly` và được rotate.
- Guest chỉ xem Landing Page và yêu cầu Magic Link; guest không được scan.

### Upload và scan

- Mỗi scan chỉ nhận một file.
- Định dạng: JPG, JPEG, PNG, WEBP hoặc PDF.
- File tối đa 10 MB; PDF tối đa 5 trang và không có mật khẩu.
- Backend kiểm tra MIME thật, không chỉ kiểm tra extension.
- Người dùng phải đăng nhập và chỉ được truy cập scan của chính mình.
- Trạng thái scan:

```text
PENDING -> PROCESSING -> COMPLETED
                      -> FAILED
```

### OCR và kết quả

- OCR giữ lại raw text để đối chiếu.
- Parser không được tự bịa tên, mô tả hoặc giá món.
- Trường không chắc chắn phải dùng `null` hoặc confidence thấp.
- Giá tiền không dùng floating-point.
- Kết quả phải hiển thị file menu gốc cạnh dữ liệu món ăn.
- MVP không tìm hoặc sinh ảnh riêng cho từng món.

### Lưu menu và lịch sử

- Kết quả scan ban đầu là bản nháp.
- Chỉ menu được người dùng xác nhận mới được xem là đã lưu.
- Chỉ owner được xem, sửa, lưu hoặc mở lại menu.
- Việc sửa dữ liệu không được ghi đè raw OCR.

### Bill và chia hóa đơn

- Đây là công cụ tính tiền, không phải hệ thống gửi order đến nhà hàng.
- User chọn món và số lượng; server tính subtotal.
- Có thể thêm service charge, tax, discount hoặc other fee.
- Hỗ trợ phí cố định và phần trăm.
- Discount không được làm tổng tiền âm.
- Tổng các phần chia phải bằng chính xác tổng bill.
- Digital Receipt dùng snapshot để menu thay đổi sau đó không làm đổi hóa đơn.
- Bill đã finalized không được chỉnh trực tiếp.

## 3. Nguyên tắc triển khai task

Không làm toàn bộ task tuần tự từng cái một, nhưng cũng không làm tự do không
theo dependency.

Quy tắc:

1. Các luồng độc lập được chạy song song.
2. Trong một luồng, task sau chỉ hoàn tất khi dependency đã merge vào `dev`.
3. Có thể bắt đầu sớm phần interface, mock, UI state hoặc test skeleton.
4. Không được merge phần tích hợp nếu dependency thật chưa có.
5. Mỗi task dùng một branch và một Pull Request riêng.
6. Không gom nhiều issue vào cùng branch.

## 4. Luồng triển khai Sprint 1

Mục tiêu Sprint 1 là có vertical slice chạy được:

```text
Magic Link -> Upload -> Processing -> File gốc + Structured Result
```

### 4.1 Nền tảng dùng chung

```text
S1-01 Chốt MVP Contract                 [Done]
  ├─> S1-02 Viết Skill cho Agent
  ├─> S1-03 Database + Migration
  ├─> S1-05 Router + Layout + Design System
  └─> S1-17 Lựa chọn và tích hợp OCR

S1-03 Database
  -> S1-04 API foundation
```

- `S1-02` giúp agent hiểu cấu trúc, contract và quy trình của MenuScan.
- `S1-03` tạo schema Magic Link, session, scan, OCR, menu và food item.
- `S1-04` tạo FastAPI startup, router, config, CORS, error handler và health.
- `S1-05` tạo nền tảng frontend và component dùng chung.
- `S1-17` đánh giá, chọn và bọc OCR provider bằng interface.

### 4.2 Luồng Magic Link

```text
S1-04 API foundation
  -> S1-06 Email service
  -> S1-07 Request Magic Link
  -> S1-08 Verify Magic Link
  -> S1-09 Access/Refresh/Logout/Me
  -> S1-10 Integration test Auth

S1-05 FE foundation + S1-09 Session API
  -> S1-11 HTTP Client + AuthProvider
  -> S1-12 Magic Link UI
  -> S1-13 Landing Page
```

Điểm bàn giao:

- BE cung cấp endpoint và response đúng contract.
- FE có thể dùng mock trước, sau đó thay bằng API thật.
- QA xác nhận token một lần, expiry, resend, refresh rotation và cookie flags.
- Sơ đồ auth phải được đổi từ password sang Magic Link.

### 4.3 Luồng upload và storage

```text
S1-03 Database + S1-04 API foundation
  -> S1-14 Object Storage

S1-05 FE foundation + S1-11 AuthProvider
  -> S1-15 Upload UI

S1-09 Auth API + S1-14 Storage
  -> S1-16 Upload API + Scan Session
```

Điểm bàn giao:

- FE validate sơ bộ để cải thiện UX.
- BE luôn validate lại file và quyền user.
- Storage chỉ lưu object key trong database.
- Bucket/file không public; truy cập qua endpoint hoặc signed URL ngắn hạn.

### 4.4 Luồng OCR, parser và dịch

```text
S1-17 OCR provider
  -> S1-18 Parser + chuẩn hóa dữ liệu
  -> S1-19 Phát hiện ngôn ngữ + dịch
```

Output tối thiểu của mỗi món:

- Tên gốc và tên dịch nếu có.
- Mô tả gốc và mô tả dịch nếu có.
- Giá, currency, category và confidence nếu nhận diện được.
- `null` cho dữ liệu không chắc chắn.

### 4.5 Ghép pipeline và hiển thị kết quả

```text
S1-16 Upload API
  + S1-17 OCR
  + S1-18 Parser
  + S1-19 Translation
  -> S1-20 Scan orchestration
  -> S1-21 Status/Source/Result API

S1-15 Upload UI + S1-21 Result API
  -> S1-22 Processing + Result UI

S1-10 Auth QA + S1-12 Magic Link UI + S1-22 Result UI
  -> S1-23 End-to-End test
```

Sprint 1 chỉ hoàn thành khi demo được toàn bộ luồng, không phải khi từng module
chạy riêng lẻ.

## 5. Luồng triển khai Sprint 2

Sprint 2 bắt đầu sau khi vertical slice Sprint 1 ổn định.

### 5.1 Review, lưu và Dashboard

```text
S1-21 Result API
  -> S2-01 Edit Result API
  -> S2-02 Edit Result UI
  -> S2-03 Confirm + History
  -> S2-04 Dashboard Summary API
  -> S2-05 Dashboard UI
```

### 5.2 Camera và tìm kiếm

```text
S1-15 Upload UI + S1-16 Upload API
  -> S2-06 Camera

S2-03 Saved Menu/History
  -> S2-07 Search API
  -> S2-08 Search UI
```

Camera chỉ tạo file đầu vào; ảnh vẫn phải đi qua cùng validation và pipeline
scan như upload.

### 5.3 Billing và Digital Receipt

```text
S1-03 Database + S2-03 Confirmed Menu
  -> S2-09 Billing Database
  -> S2-10 Draft Bill
  -> S2-11 Fee/Tax/Discount
  -> S2-12 Split Bill

S2-02 Result UI + S2-10..12 Billing API
  -> S2-13 Billing UI
  -> S2-14 Digital Receipt
```

### 5.4 Hardening, release và tài liệu

```text
S2-15 OCR Accuracy
S2-16 Responsive + Accessibility
S2-17 Error/Empty/Toast
  -> S2-18 Performance + Browser
  -> S2-19 Security QA
  -> S2-20 End-to-End QA
  -> S2-21 Production Config
  -> S2-22 Backend/Data Deployment
  -> S2-23 Frontend Deployment + Smoke Test
```

Sau khi sản phẩm có bằng chứng chạy thật:

```text
S2-24..28 Báo cáo Chương 1–5
  -> S2-29 Slide + kịch bản
  -> S2-30 Video demo
```

Không ghi trong báo cáo rằng một tính năng đã hoàn thành nếu chưa có PR merge,
test hoặc production evidence.

## 6. Trách nhiệm hiện tại của từng thành viên

### Hà

- API foundation, frontend foundation, storage, upload API và orchestration.
- Performance, security/E2E review và toàn bộ DevOps.
- Review công việc của nhóm và kiểm soát việc tích hợp vào `dev`.

### Đức

- Viết Skill cho Agent.
- Verify Magic Link, session API, Auth QA và Magic Link UI.
- Edit menu, Dashboard, responsive và Chương 1 báo cáo.

### Tài

- Database, OCR, parser, translation và Upload UI.
- Camera và backend Billing.
- Chương 4 lược đồ lớp.

### Linh

- Email service, request Magic Link và AuthProvider.
- Landing Page, status/result API và result UI.
- Search, split bill, Digital Receipt, UI states, Chương 3, Slide và Video.

Ownership không có nghĩa làm một mình. Khi task cần contract của người khác,
hai bên phải thống nhất interface trước khi code.

## 7. Quy trình làm việc hằng ngày

### Bắt đầu task

1. Chỉ nhận task ở `In Progress` đã được team thống nhất.
2. Đọc mục `Dependencies`; kiểm tra PR dependency đã merge chưa.
3. Đồng bộ `dev`.
4. Tạo branch theo mã task hiện tại.

```bash
git switch dev
git pull --ff-only origin dev
gh issue develop <issue-number> --base dev --checkout --name <task-code>
```

Ví dụ:

```bash
gh issue develop 31 --base dev --checkout --name s1-03
```

### Trong khi làm

- Chỉ sửa phạm vi của issue.
- Nếu cần thay contract, dừng và thống nhất trước với nhóm.
- Không dựa vào file/sơ đồ cũ nếu khác MVP Contract.
- Viết test cùng task, không để tất cả test đến cuối Sprint.
- Có thể dùng mock/interface để làm song song nhưng phải ghi rõ trong PR.

### Tạo Pull Request

```bash
git push -u origin HEAD
gh pr create --base dev --fill
```

PR phải có:

- `Closes #<issue-number>`.
- Tóm tắt thay đổi.
- Cách kiểm tra.
- Screenshot/video nếu là UI.
- API example hoặc migration evidence nếu là BE/DB.
- Known limitations nếu còn phần đang dùng mock.

### Review và merge

```text
Todo -> In Progress -> Review -> Done
```

- Chuyển `Review` khi PR đã mở và CI pass.
- Hà review toàn bộ PR; owner module liên quan hỗ trợ review contract.
- Không tự merge khi còn comment chưa xử lý.
- Chỉ chuyển `Done` sau khi PR merge vào `dev`.
- Task sau dependency chỉ dùng code đã merge, không dựa vào branch cá nhân.

## 8. Definition of Done

Một task chỉ được xem là hoàn thành khi:

- Đúng nghiệp vụ và API/schema đã chốt.
- Không thêm chức năng ngoài phạm vi.
- Có validation và xử lý lỗi.
- Có test phù hợp và CI pass.
- Không lộ token, secret, raw exception hoặc dữ liệu user khác.
- Tài liệu/sơ đồ liên quan được cập nhật.
- PR được review và merge vào `dev`.
- Issue được đóng và Project chuyển `Done`.

## 9. Khi nào phải dừng và hỏi nhóm?

Dừng triển khai nếu gặp một trong các trường hợp:

- Figma khác MVP Contract.
- FE và BE đang dùng hai response schema khác nhau.
- Task yêu cầu endpoint chưa có trong API contract.
- Cần thêm field hoặc bảng làm thay đổi migration của người khác.
- Dependency chưa merge nhưng cần code tích hợp thật.
- Yêu cầu mới làm thay đổi In scope/Out of scope.
- Không rõ dữ liệu thiếu nên để `null`, fallback hay báo lỗi.

## 10. Kịch bản trình bày ngắn cho nhóm

Bạn có thể nói với nhóm như sau:

> MenuScan có hai Sprint phát triển. Sprint 1 tạo vertical slice cốt lõi:
> đăng nhập bằng Magic Link, upload menu, OCR, phân tích/dịch và hiển thị file
> gốc cùng kết quả. Các luồng Database, Auth, Frontend và OCR chạy song song,
> sau đó ghép tại Scan Orchestration và kiểm thử E2E. Sprint 2 cho phép sửa và
> lưu kết quả, xem Dashboard/lịch sử, tìm kiếm, chọn món, thêm phí, chia bill,
> tạo Digital Receipt, rồi hardening, deploy và hoàn thiện báo cáo.
>
> Mỗi task có dependency. Chúng ta có thể bắt đầu interface hoặc mock song
> song, nhưng không được merge phần tích hợp trước dependency. Mỗi task dùng
> một branch và một PR vào `dev`. CI pass, review xong và merge thì task mới
> được Done. MVP không có password, guest scan, thanh toán online hay ảnh món
> do AI sinh.

