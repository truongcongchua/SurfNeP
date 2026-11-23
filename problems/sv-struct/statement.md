# Nhận hồ sơ sinh viên qua dữ liệu nhị phân

`sv_client` đóng gói thông tin sinh viên thành **bản ghi nhị phân** và gửi qua TCP. Bạn viết phía
server: `./sv_server <cổng> <tệp log>`. Phục vụ lần lượt từng client là đủ.

## Định dạng một bản ghi (mọi số nguyên dùng thứ tự mạng, big-endian, không có padding)

| Trường | Kích thước | Ghi chú |
|---|---|---|
| `mssv` | 4 byte, `uint32` | |
| `name_len` | 1 byte | 1 … 100 |
| `name` | `name_len` byte | UTF-8, không chứa `\n` |
| `year` | 2 byte, `uint16` | |
| `month` | 1 byte | 1 … 12 |
| `day` | 1 byte | 1 … 31 |
| `gpa100` | 2 byte, `uint16` | điểm × 100, 0 … 400 |

Một client có thể gửi **nhiều bản ghi** liên tiếp trên cùng kết nối.

## Xử lý mỗi bản ghi
- **Hợp lệ**: in ra màn hình **và** ghi nối tiếp vào tệp log một dòng:
  ```
  <IP client> <YYYY-MM-DD HH:MM:SS> <mssv> <name> <YYYY-MM-DD> <gpa, 2 chữ số thập phân>
  ```
  rồi gửi `OK\n` cho client. Thời gian là thời điểm server nhận bản ghi (giờ địa phương của máy).
- **Không hợp lệ** (`name_len = 0` hoặc > 100, tháng/ngày/gpa ngoài khoảng): gửi `ERROR\n` rồi
  **đóng** kết nối với client đó.

## Ràng buộc và bộ chấm kiểm tra
- Kiểm tra đủ biên: tháng 1–12, ngày 1–31 (không cần kiểm tra ngày có tồn tại trong tháng), gpa 0–400,
  `name_len` 1–100; `mssv` tới 4294967295 (in như số không dấu); năm in đủ 4 chữ số (`0999`).
- Bản ghi có thể đến từng byte, hoặc hàng trăm bản ghi dính nhau trong một lần gửi.
- Tệp log có thể **đã có nội dung** từ trước: ghi nối tiếp. Dòng log phải xuất hiện trong tệp và trên màn
  hình **ngay** sau khi gửi `OK` (đóng tệp / `fflush`).
- Client có thể đóng hoặc mất kết nối (RST) giữa bản ghi; chương trình chạy với giới hạn 256 file descriptor
  (300 bản ghi trên một kết nối, 300 client lần lượt).

## Ví dụ dòng log

```
127.0.0.1 2026-11-20 09:00:00 20201234 Nguyễn Văn A 2002-04-10 3.99
```

## Đoạn code cho sẵn
Code mẫu chưa có hàm lấy thời gian. Hãy chép nguyên đoạn sau (cần `#include <time.h>`); IP client lấy bằng
`inet_ntoa(client_addr.sin_addr)` như `udp_receiver.c`.

```c
char now[32];
time_t t = time(NULL);
strftime(now, sizeof(now), "%Y-%m-%d %H:%M:%S", localtime(&t));
```

## Bẫy
Đừng `recv` thẳng vào một `struct`: trình biên dịch chèn **padding** và số nguyên nằm theo thứ tự
host. Hãy lặp `recv` tới khi đủ byte của từng phần, rồi giải mã thủ công (`memcpy` từng trường) và `ntohl`/`ntohs`.
