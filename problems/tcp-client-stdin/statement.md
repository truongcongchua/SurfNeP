# Gửi dữ liệu từ bàn phím qua TCP

Viết chương trình **client** chạy bằng:

```
./tcp_client <địa chỉ IP> <cổng>
```

- Kết nối TCP tới server tại `<địa chỉ IP>:<cổng>`.
- Đọc dữ liệu từ bàn phím (stdin) và gửi tới server **ngay khi đọc được từng dòng**. Không được
  đợi đọc hết stdin rồi mới gửi.
- Khi stdin kết thúc (EOF, tức `Ctrl+D`): đóng kết nối và thoát với mã `0`.
- Nếu không kết nối được (sai địa chỉ, server không mở cổng): in thông báo lỗi ra `stderr` và
  thoát với mã **khác 0**, không treo.
- Dữ liệu gửi đi phải **giống hệt** dữ liệu nhập vào, kể cả ký tự xuống dòng.

## Bài khởi động
Bài này ghép hai kỹ năng đã có bài luyện riêng. Nếu còn lúng túng, làm trước:
- `stdin-forward` (Chuyển tiếp stdin ra stdout bằng read/write): vòng lặp `read(STDIN_FILENO, ...)`, xử lý đúng `n` byte, gửi ngay không đợi EOF.
- `tcp-client-send` (Client gửi một thông điệp): `inet_addr` + `htons(atoi(...))` + `connect`, rồi `send` và `close`.

Bài này chỉ thay `write(STDOUT_FILENO, ...)` của `stdin-forward` bằng `send(client_socket, ...)`, sau khi kết nối như `tcp-client-send`.

## Ràng buộc
- Dữ liệu nhập là byte bất kỳ (có thể chứa `0x00`, `\r`, dòng rất dài tới 200 KB, tổng tới vài MB): gửi **đúng
  từng byte** (đừng dùng `fgets` + `strlen`). stdin rỗng thì kết nối rồi đóng, không gửi gì.
- Server có thể ngừng đọc một lúc: `send` trên socket blocking sẽ **chờ** cho tới khi gửi hết, không được bỏ dữ liệu.

## Gợi ý
Như `tcp_client.c` (`inet_addr`, `connect`). Đọc stdin bằng `read(STDIN_FILENO, buffer, sizeof(buffer))` (lab08):
nó trả về ngay khi có một dòng, trả `0` khi hết stdin, và cho biết đúng số byte đã đọc (kể cả `0x00`).

## Bộ chấm kiểm tra
Bộ chấm dựng một server giả, chạy chương trình của bạn với tham số `127.0.0.1 <cổng>`, rồi ghi
vào stdin của nó. Server giả kiểm tra từng dòng có đến kịp thời hay không và toàn bộ dữ liệu có
khớp không.
