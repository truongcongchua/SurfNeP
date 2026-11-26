# Đăng ký, đăng nhập và tối đa N client

Mảnh "tài khoản người dùng" của bài tập lớn đặt vé máy bay. Viết server TCP chạy bằng `./server <cổng> <N>`:
phục vụ **đồng thời** tối đa `N` client (1 ≤ N ≤ 50), mỗi kết nối là một **phiên** có trạng thái *chưa đăng nhập* /
*đã đăng nhập*. Tài khoản lưu trong tệp `accounts.txt` ở thư mục hiện hành. Chọn kỹ thuật `select()` hoặc đa luồng
(nhớ mutex); đa tiến trình không phù hợp vì các client dùng chung danh sách tài khoản.

## Tệp `accounts.txt`

Mỗi dòng một tài khoản `<user> <pass>` (cách nhau đúng một dấu cách), nạp vào bộ nhớ khi khởi động. Tệp có sẵn một vài
tài khoản; có tối đa 1000 tài khoản. Tài khoản mới đăng ký phải **được ghi nối tiếp vào cuối tệp ngay** (dòng
`<user> <pass>\n`, đã `fflush`/`fclose`), để khởi động lại server vẫn còn.

## Kết nối

- Đang có ít hơn `N` client: gửi `100 OK WELCOME`.
- Đã đủ `N` client: gửi `500 FULL` rồi đóng kết nối đó ngay (không chiếm chỗ).
- Client rời đi (`QUIT`, đóng, hoặc mất kết nối đột ngột) thì trả lại chỗ **và** đăng xuất tài khoản của phiên đó.

## Lệnh

Mỗi lệnh là một dòng `\n` (bỏ **một** `\r` cuối dòng nếu có, tối đa 1000 byte). Các thành phần cách nhau bởi **đúng một
dấu cách**. Luật `user`/`pass` giống bài *fly-parse*: `user` gồm 1–32 ký tự `a-z0-9`; `pass` gồm 4–32 ký tự có mã
`0x21`–`0x7E`.

| Lệnh | Phản hồi |
|---|---|
| `REGISTER <user> <pass>` | sai cú pháp → `201 INVALID`; `user` đã có → `200 USERNAME IN USE`; ngược lại ghi tệp và `100 OK` (không tự đăng nhập) |
| `LOGIN <user> <pass>` | sai cú pháp → `201 INVALID`; phiên này **đã đăng nhập** → `207 ALREADY LOGGED IN`; sai tên hoặc sai mật khẩu → `203 DENIED`; đúng nhưng tài khoản đang được **một phiên khác** dùng → `207 ALREADY LOGGED IN`; ngược lại `100 OK <user>` |
| `LOGOUT` | chưa đăng nhập → `204 LOGIN FIRST`; ngược lại `100 OK` |
| `WHOAMI` | chưa đăng nhập → `204 LOGIN FIRST`; ngược lại `100 OK <user>` |
| `QUIT` | `100 OK` rồi đóng kết nối |
| `LOGOUT`, `WHOAMI`, `QUIT` kèm tham số | `201 INVALID` |
| mọi thứ khác (tên lệnh lạ, `login`, dòng trống) | `999 UNKNOWN ERROR` |

Thứ tự kiểm tra của `LOGIN`: cú pháp → phiên đã đăng nhập → tên/mật khẩu → tài khoản đang bị dùng. Tên và mật khẩu
phân biệt hoa thường. Một tài khoản chỉ được đăng nhập ở **một** phiên tại một thời điểm.

## Ví dụ (N = 2, `accounts.txt` có `an 1234`)

```
A: (kết nối)             ← 100 OK WELCOME
A: WHOAMI                ← 204 LOGIN FIRST
A: LOGIN an 12345        ← 203 DENIED
A: LOGIN an 1234         ← 100 OK an
B: (kết nối)             ← 100 OK WELCOME
B: LOGIN an 1234         ← 207 ALREADY LOGGED IN
B: REGISTER an 9999      ← 200 USERNAME IN USE
B: REGISTER binh abcd    ← 100 OK            (thêm dòng "binh abcd" vào accounts.txt)
C: (kết nối)             ← 500 FULL (bị đóng)
A: QUIT                  ← 100 OK
B: LOGIN an 1234         ← 100 OK an
```

## Ràng buộc và bộ chấm kiểm tra
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng chục lệnh dính nhau trong một lần gửi (kể cả sau `QUIT`: phần sau bị bỏ).
- Nhiều client có thể **cùng lúc** `REGISTER` một tên hoặc `LOGIN` một tài khoản: chỉ đúng một người thành công.
- Lệnh bị từ chối (`201`, `200`...) **không được** ghi gì vào `accounts.txt`.
- Client có thể mất kết nối đột ngột; bộ chấm chạy 300 lượt kết nối-ngắt với giới hạn 256 file descriptor.

## Kiến thức nền
§4.3: giao thức **theo phiên** và xác thực người dùng; đọc/ghi tệp `fopen`/`fgets`/`fprintf`/`fflush` (lab07);
giới hạn số client xem `kv-max-n`.
