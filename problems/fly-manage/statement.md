# Quản lý vé đã đặt (xem, hủy, đổi, in)

Chức năng "quản lý vé đã đặt" (3 điểm) của bài tập lớn đặt vé máy bay: xem chi tiết, **hủy vé có hoàn tiền theo thời gian còn lại**, **đổi
sang chuyến khác có chênh lệch giá và phí**, và **in vé** (gửi nội dung có độ dài như bài *fly-print-client*, nhìn từ phía server).

Viết server TCP `./server <cổng> <ngày hiện tại> <giờ hiện tại>`, ví dụ `./server 9000 2026-12-01 08:00`. Hai tham số cuối là **giờ của
hệ thống** do bộ chấm đặt để mọi lần chấm cho cùng kết quả (khi làm bài tập lớn thật bạn thay bằng `time(NULL)`). Phục vụ nhiều
client cùng lúc (`select` hoặc đa luồng).

## Tệp (nạp khi khởi động, thay đổi chỉ cần giữ trong bộ nhớ)

- `flights.txt`: như các bài trước (mã chuyến là duy nhất). Số ghế thay đổi khi hủy/đổi vé.
- `accounts.txt`: `<user> <pass>`; `wallets.txt`: `<user> <số dư>` (không có dòng thì số dư 0).
- `tickets.txt`: `<số vé> <user> <chuyến> <ngày> <hạng> <hành khách> <giá đã trả> <trạng thái>` với trạng thái `PAID` hoặc `CANCELLED`.

## Lệnh (mỗi lệnh một dòng `\n`, bỏ `\r` cuối; các thành phần cách nhau đúng một dấu cách)

Server không chào. Chưa đăng nhập mà dùng lệnh cần đăng nhập → `204 LOGIN FIRST` (kiểm tra **trước** cú pháp).

| Lệnh | Phản hồi |
|---|---|
| `LOGIN <user> <pass>` | `201 INVALID` (sai cú pháp: đúng 3 thành phần), `207 ALREADY LOGGED IN` (phiên đã đăng nhập), `203 DENIED` (sai tên/mật khẩu), `100 OK <user>`. Một tài khoản có thể ở nhiều phiên |
| `SEATS <chuyến>` | (không cần đăng nhập) `100 OK <ghế ECO> <ghế BUS>`; không có chuyến `202 NOT FOUND` |
| `BALANCE` | `100 OK <số dư>` |
| `MYTICKETS` | `110 TICKETS <k>` rồi `k` dòng `<số vé> <chuyến> <ngày> <hạng> <hành khách> <giá> <trạng thái>` — mọi vé của tài khoản (kể cả đã hủy), theo thứ tự số vé tăng dần |
| `VIEW <số vé>` | `100 OK <số vé> <chuyến> <ngày> <hạng> <hành khách> <giá> <trạng thái> <giờ đi> <giờ đến>` |
| `CANCEL <số vé>` | hủy vé, hoàn tiền: `100 OK REFUNDED <số tiền>` |
| `CHANGE <số vé> <chuyến mới>` | đổi chuyến: `100 OK CHANGED <số vé> <chênh lệch>` |
| `PRINT <số vé>` | `120 FILE <n>` rồi đúng `n` byte nội dung vé |
| `QUIT` | `100 OK` rồi đóng |
| mọi thứ khác | `999 UNKNOWN ERROR` |

`BALANCE`, `MYTICKETS`, `VIEW`, `CANCEL`, `CHANGE`, `PRINT`, `SEATS` thiếu hoặc thừa thành phần: `201 INVALID` (sau khi đã qua kiểm tra đăng nhập nếu lệnh cần). Với `VIEW`, `CANCEL`, `CHANGE`, `PRINT`: số vé không có → `202 NOT FOUND`;
vé của tài khoản khác → `203 DENIED` (kiểm tra theo thứ tự này).

### Thời gian còn lại
`còn lại` = (ngày giờ khởi hành của chuyến) − (giờ hiện tại), tính bằng **phút**, giờ địa phương, không xét múi giờ/giờ mùa hè.

### CANCEL
Sau các kiểm tra chung: vé đã hủy → `209 ALREADY CANCELLED`; `còn lại ≤ 0` (đã/đang khởi hành) → `210 TOO LATE`. Ngược lại hoàn vào ví
`giá × tỉ lệ / 100` (chia nguyên, làm tròn xuống) với tỉ lệ: **90%** nếu `còn lại ≥ 72 giờ`; **70%** nếu `còn lại ≥ 24 giờ`; **30%** còn lại.
Hoàn tất: vé thành `CANCELLED`, trả 1 ghế (đúng hạng) cho chuyến, cộng ví.

### CHANGE
Vé phải `PAID` (`209` nếu đã hủy). Thứ tự kiểm tra tiếp: `chuyến mới` giống chuyến hiện tại → `201 INVALID`; chuyến hiện tại `còn lại < 180` phút → `210 TOO LATE`;
không có `chuyến mới` trong `flights.txt` → `202 NOT FOUND`; khác sân bay đi hoặc đến → `211 DIFFERENT ROUTE`; `chuyến mới` đã khởi hành
(`còn lại ≤ 0`) → `210 TOO LATE`; hết ghế hạng của vé → `205 NO SEATS`.
Giá mới = giá hạng đó của chuyến mới; `chênh lệch = giá mới − giá đã trả + 200000` (phí đổi 200000). Nếu `chênh lệch > số dư` → `206 PAYMENT FAILED`.
Ngược lại: trừ ví `chênh lệch` (nếu âm thì **cộng** ví phần tuyệt đối), vé chuyển sang chuyến mới (đổi `<chuyến>`, `<ngày>`, `<giá đã trả>` = giá mới),
trả ghế chuyến cũ, trừ ghế chuyến mới, và phản hồi `100 OK CHANGED <số vé> <chênh lệch>` (số có dấu; âm là được hoàn).

### PRINT
Nội dung là văn bản sau (mỗi dòng kết thúc `\n`, `n` là số byte của toàn bộ, **không** có ký tự thừa sau đó):
```
===== VE DIEN TU =====
So ve: <số vé>
Hanh khach: <hành khách>
Chuyen bay: <chuyến> <đi> -> <đến>
Ngay: <ngày> <giờ đi> - <giờ đến>
Hang: <hạng>
Gia ve: <giá>
Trang thai: <trạng thái>
In luc: <ngày hiện tại> <giờ hiện tại>
```

## Ví dụ (giờ hiện tại 2026-12-01 08:00; vé của `an`: `...01` chuyến `VN501` giá 1.000.000, khởi hành 2026-12-04 08:00)

```
A: LOGIN an 1234           ← 100 OK an
A: CANCEL 7380000000001    ← 100 OK REFUNDED 900000        (còn đúng 72 giờ → 90%)
A: CANCEL 7380000000001    ← 209 ALREADY CANCELLED
A: CANCEL 7380000000006    ← 210 TOO LATE                  (VN506 khởi hành đúng 08:00)
A: CHANGE 7380000000002 VN510 ← 100 OK CHANGED 7380000000002 400000   (1.200.000 − 1.000.000 + 200.000)
A: PRINT 7380000000002     ← 120 FILE 198 ... (nội dung vé)
```

## Ràng buộc và bộ chấm kiểm tra
- Bộ chấm chạy nhiều giá trị `<ngày hiện tại> <giờ hiện tại>` (kể cả qua nửa đêm, qua tháng, qua năm) với cùng các tệp; tính đúng sai ở **đúng biên** (72 giờ, 24 giờ, 3 giờ, ±1 phút).
- Số tiền dùng số nguyên 64 bit. Nội dung vé có thể bị đọc từng byte: `n` phải khớp **đúng** số byte gửi.
- Nhiều phiên cùng tài khoản có thể thao tác cùng một vé: kết quả như thực hiện tuần tự (hoàn tiền một lần, trả ghế một lần).
- Lệnh có thể bị cắt vụn từng byte hoặc dính nhau; client có thể mất kết nối đột ngột.

## Kiến thức nền
`sscanf`, `mktime` hoặc tự đổi ngày ra số phút (thư viện C chung); gửi `120 FILE n` + dữ liệu như phía server của *length-prefix* (đếm byte bằng `snprintf` trả về).
