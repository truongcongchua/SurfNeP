# sv_server nhận hồ sơ sinh viên nhị phân (Bài tập 2.4–2.5)

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

## Ví dụ dòng log

```
127.0.0.1 2026-11-20 09:00:00 20201234 Nguyễn Văn A 2002-04-10 3.99
```

## Bẫy
Đừng `recv` thẳng vào một `struct`: trình biên dịch chèn **padding** và số nguyên nằm theo thứ tự
host. Hãy đọc từng trường (hoặc đọc đủ byte rồi giải mã thủ công) và `ntohl`/`ntohs`.
