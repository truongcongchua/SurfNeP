# Thi thử 3: Đặt vé máy bay qua TCP

> **Thời gian: 90 phút.** Chỉ các test mẫu hiển thị chi tiết; các test còn lại chỉ báo đúng/sai.

Viết server bán vé máy bay hạng phổ thông: `./server <cổng> <N>`.
- `N` (1 ≤ N ≤ 50): số client **kết nối đồng thời** tối đa.
- Khi khởi động đọc ba tệp trong thư mục hiện hành: `flights.txt` (mỗi dòng
  `<mã> <hãng> <đi> <đến> <ngày> <giờ đi> <giờ đến> <giá ECO> <ghế ECO> <giá BUS> <ghế BUS>`, **chỉ dùng hạng ECO**),
  `accounts.txt` (`<user> <pass>` mỗi dòng) và `wallets.txt` (`<user> <số dư>` mỗi dòng).
  Mọi thay đổi chỉ cần giữ trong bộ nhớ.

Được dùng bất kỳ kỹ thuật nào trong code mẫu: `select`, đa luồng (nhớ mutex), v.v.

## Kết nối
- Đang có ít hơn `N` client: gửi `WELCOME`. Ngược lại gửi `FULL` và đóng kết nối đó.
- Client rời đi (bằng `QUIT` hoặc đóng đột ngột) thì giải phóng chỗ. **Vé đã mua vẫn giữ**, gắn với tài khoản.

## Lệnh (mỗi lệnh một dòng, bỏ `\r` cuối dòng; các thành phần cách nhau đúng một dấu cách)

| Lệnh | Điều kiện | Phản hồi |
|---|---|---|
| `LOGIN <user> <pass>` | đúng tên và mật khẩu | `OK <user>`; sai thì `FAIL` và **trạng thái đăng nhập cũ giữ nguyên**. Được đăng nhập lại để đổi tài khoản, và một tài khoản dùng được ở nhiều kết nối |
| `SEARCH <đi> <đến> <ngày>` | | `FLIGHTS <k>` rồi `k` dòng `<mã> <giờ đi> <giờ đến> <giá ECO>` cho các chuyến khớp đi/đến/ngày còn **ít nhất 1 ghế ECO**, theo thứ tự trong tệp |
| `BOOK <mã> <ngày>` | đã LOGIN | mua 1 vé ECO: `TICKET <id>` · `NOT_FOUND` nếu không có (mã, ngày) · `NO_SEATS` nếu hết ghế ECO · `NO_MONEY` nếu số dư ví nhỏ hơn giá |
| `MYTICKETS` | đã LOGIN | `TICKETS <k>` rồi `k` dòng `<id> <mã> <ngày>` của **tài khoản** này, `id` tăng dần |
| `CANCEL <id>` | đã LOGIN | `REFUNDED <số tiền>` (hoàn đủ giá vé vào ví, trả ghế, vé biến mất) · `NOT_FOUND` nếu không có vé đó · `NOT_YOURS` nếu vé của tài khoản khác |
| `BALANCE` | đã LOGIN | `BALANCE <số dư>` |
| `QUIT` | | `BYE` rồi đóng |
| `BOOK`, `MYTICKETS`, `CANCEL`, `BALANCE` khi chưa LOGIN | | `LOGIN_FIRST` (kiểm tra **trước** cú pháp) |
| mọi thứ khác (sai tên lệnh, thiếu/thừa thành phần, dòng trống) | | `ERROR` |

`id` vé có dạng `T` + 4 chữ số, đánh số **toàn server** từ `T0001` theo thứ tự mua thành công, và **không bao giờ dùng lại**
(kể cả sau `CANCEL`). Số dư và giá là số nguyên.

## Ví dụ (N = 2)

```
A: (kết nối)            ← WELCOME
A: BOOK VN001 2026-12-20  ← LOGIN_FIRST
A: LOGIN an 1234        ← OK an
A: SEARCH HAN SGN 2026-12-20 ← FLIGHTS 3 … (3 dòng)
A: BOOK VN001 2026-12-20 ← TICKET T0001
B: (kết nối)            ← WELCOME
B: LOGIN an 1234        ← OK an
B: MYTICKETS            ← TICKETS 1
B:                      ← T0001 VN001 2026-12-20
C: (kết nối)            ← FULL
A: CANCEL T0001         ← REFUNDED 1000000
B: MYTICKETS            ← TICKETS 0
```

## Ràng buộc (test ẩn kiểm tra đúng các điều này)
- Các thành phần cách nhau một dấu cách; dòng có thể kết thúc bằng `\r\n`; mỗi dòng tối đa 1000 byte.
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng trăm lệnh dính nhau trong một lần gửi.
- Nhiều client **cùng lúc** tranh một ghế: mỗi ghế chỉ bán một lần và mỗi `id` chỉ cấp một lần.
- Kết nối mới luôn ở trạng thái **chưa LOGIN**, kể cả khi dùng lại chỗ của client cũ.
- Client có thể mất kết nối đột ngột (RST); chương trình chạy với giới hạn 256 file descriptor, bộ chấm cho 300 kết nối
  vào-ra và 300 kết nối bị `FULL`.
