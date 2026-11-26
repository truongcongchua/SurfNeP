# Đặt vé và thanh toán

Phần nặng nhất của bài tập lớn đặt vé máy bay: nhiều khách **cùng lúc** tranh những ghế cuối cùng, ghế phải được
**giữ** trong lúc khách thanh toán, và **tự trả lại** nếu khách không trả tiền kịp. Viết server TCP chạy bằng
`./server <cổng> <N> <T>`:

- `N` (1 ≤ N ≤ 50): số client **kết nối đồng thời** tối đa.
- `T` (1 ≤ T ≤ 3600): số giây được giữ chỗ trước khi phải thanh toán.

Server nạp ba tệp trong thư mục hiện hành khi khởi động: `flights.txt` (định dạng bài *flight-filter*; số ghế còn lại
thay đổi theo các lần đặt), `accounts.txt` (`<user> <pass>` mỗi dòng) và `wallets.txt` (`<user> <số dư>` mỗi dòng;
tài khoản không có dòng nào thì số dư 0). Tất cả chỉ cần giữ trong bộ nhớ. Trạng thái dùng chung cho mọi client nên
không dùng `fork`; chọn `select()` hoặc đa luồng (nhớ mutex).

## Kết nối
- Còn chỗ: gửi `100 OK WELCOME`. Đã đủ `N` client: gửi `500 FULL` rồi đóng kết nối đó.
- Client rời đi (kể cả đột ngột) trả lại chỗ, đăng xuất, và **trả lại ghế của mọi chỗ giữ chưa thanh toán** do phiên đó
  đặt (các vé **đã thanh toán** thì giữ nguyên).

## Lệnh

Một dòng `\n` (bỏ **một** `\r` cuối dòng nếu có, tối đa 1000 byte), các thành phần cách nhau **đúng một dấu cách**.
`<ngày>` là ngày hợp lệ `YYYY-MM-DD` (như bài *fly-parse*). Tên lệnh phân biệt hoa thường.

| Lệnh | Phản hồi |
|---|---|
| `LOGIN <user> <pass>` | như bài *fly-auth* nhưng một tài khoản được đăng nhập ở **nhiều phiên**: sai cú pháp `201 INVALID`, phiên đã đăng nhập `207 ALREADY LOGGED IN`, sai tên/mật khẩu `203 DENIED`, đúng `100 OK <user>` |
| `SEATS <chuyến> <ngày>` | (không cần đăng nhập) `100 OK <ghế ECO> <ghế BUS>` còn trống ngay lúc này; không có chuyến đó `202 NOT FOUND` |
| `BALANCE` | `100 OK <số dư>` |
| `BOOK <chuyến> <ngày> <hạng> <số khách>` | giữ ghế: `100 OK HOLD <PNR> <số tiền> <hạn>` |
| `PAY <PNR> WALLET` | trừ ví: `100 OK PAID <PNR>` |
| `PAY <PNR> CARD <số thẻ> <MM/YY> <CVV>` | trả bằng thẻ: `100 OK PAID <PNR>` |
| `RELEASE <PNR>` | bỏ chỗ giữ, trả ghế: `100 OK` |
| `QUIT` | `100 OK` rồi đóng |
| lệnh khác, dòng trống | `999 UNKNOWN ERROR` |

`BALANCE`, `BOOK`, `PAY`, `RELEASE` yêu cầu đã đăng nhập, nếu chưa thì `204 LOGIN FIRST` (kiểm tra **trước** mọi thứ khác).
Thiếu/thừa thành phần hoặc sai định dạng → `201 INVALID`.

### BOOK
`hạng` là `ECO`/`BUS`, `số khách` là một chữ số `1`–`9`. Thứ tự kiểm tra: đăng nhập → cú pháp (`201`) → chuyến và ngày có
trong tệp (`202 NOT FOUND`) → còn **ít nhất** `số khách` ghế hạng đó (`205 NO SEATS`). Thành công thì **trừ ghế ngay**.
- `PNR`: 6 ký tự ngẫu nhiên từ `A-Z0-9`, **không trùng** với bất kỳ PNR nào đã cấp từ lúc server khởi động.
- `số tiền` = giá hạng đó × số khách.
- `hạn` = giờ địa phương của server lúc hết hạn giữ chỗ (`giờ hiện tại + T giây`) dạng `HH:MM:SS`.

### PAY
Thứ tự kiểm tra: đăng nhập → số thành phần/kiểu (`201`) → PNR có tồn tại (`202`) → PNR là của **tài khoản** này (`203 DENIED`)
→ đã thanh toán (`209 ALREADY PAID`) → đã hết hạn (`208 EXPIRED`) → thanh toán (`206 PAYMENT FAILED` nếu thất bại,
chỗ giữ **vẫn còn** để thử lại).
- `WALLET`: thất bại nếu số dư nhỏ hơn số tiền; thành công thì trừ số dư.
- `CARD`: `số thẻ` đủ 16 chữ số **và** đúng thuật toán **Luhn**; `MM/YY` đúng dạng hai chữ số `/` hai chữ số, `MM` từ
  `01` đến `12`, và chưa qua hạn (tháng hiện tại vẫn còn hạn); `CVV` đúng 3 chữ số. Sai bất cứ điều nào → `206`.
  (Đây là thanh toán **mô phỏng**, không có cổng thanh toán thật.)

### RELEASE
Cùng thứ tự `202`/`203`/`209`/`208` như `PAY`; đang giữ chỗ thì trả ghế và PNR không còn tồn tại (`PAY` sau đó cho `202`).

### Hết hạn
Chỗ giữ quá `T` giây chưa thanh toán thì **tự trả ghế** — dù không client nào gửi lệnh trong lúc đó; mọi lệnh sau đó
đều phải thấy ghế đã được trả. `PAY`/`RELEASE` PNR đã hết hạn cho `208 EXPIRED`.

## Ví dụ (`T = 60`; `VN001` HAN→SGN ngày 2026-12-20 còn 3 ghế ECO, giá 1.000.000)

```
A: LOGIN an 1234               ← 100 OK an
A: BOOK VN001 2026-12-20 ECO 2 ← 100 OK HOLD K3F9QX 2000000 14:03:27
B: LOGIN binh abcd             ← 100 OK binh
B: BOOK VN001 2026-12-20 ECO 2 ← 205 NO SEATS
B: SEATS VN001 2026-12-20      ← 100 OK 1 2
A: PAY K3F9QX WALLET           ← 100 OK PAID K3F9QX
B: PAY K3F9QX WALLET           ← 203 DENIED
A: BALANCE                     ← 100 OK 48000000
```

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là `flights.txt`/`accounts.txt`/`wallets.txt` của bộ chấm (12 chuyến, vài chuyến chỉ còn 1–3 ghế, một số hạng BUS hết ghế).
- Số tiền và số dư dùng số nguyên 64 bit; giá không quá 10^8.
- Lệnh có thể bị cắt vụn từng byte hoặc hàng chục lệnh dính nhau; client có thể mất kết nối đột ngột; giới hạn 256 file descriptor.
- Nhiều client **cùng lúc** tranh ghế: mỗi ghế chỉ bán một lần, số ghế không bao giờ âm hay vượt số ban đầu.
- Bộ chấm sẽ chờ tới `T + 1.5` giây thật để kiểm tra hết hạn (với `T = 2`).

## Kiến thức nền
§3.4–3.5: dữ liệu dùng chung giữa nhiều client (mutex nếu dùng luồng); §4.3: giao thức theo phiên, mã trạng thái.
`time`, `localtime`, `strftime`, `rand`/`srand` là thư viện C chung (không thuộc lập trình mạng), được dùng thoải mái.
**Được phép dùng thêm** (không bắt buộc): `signal(SIGPIPE, SIG_IGN)` hoặc cờ `MSG_NOSIGNAL` để server không chết khi gửi
vào kết nối đã đóng.
