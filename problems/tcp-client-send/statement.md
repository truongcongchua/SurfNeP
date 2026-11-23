# Client gửi một thông điệp

Viết chương trình **client** chạy bằng:

```
./tcp_client <địa chỉ IP> <cổng> <thông điệp>
```

- Kết nối TCP tới server tại `<địa chỉ IP>:<cổng>`.
- Gửi **đúng** `<thông điệp>` (tham số dòng lệnh thứ ba) cộng một ký tự `\n` ở cuối. Không gửi thêm byte nào khác
  (đặc biệt không gửi `'\0'`).
- Gửi xong thì đóng kết nối và thoát với mã `0`. Client không nhận gì từ server.
- Không kết nối được (sai địa chỉ, server không mở cổng): in lỗi ra `stderr` bằng `perror` và thoát với mã **khác 0**,
  không treo.
- Sai số tham số dòng lệnh (không đúng 3 tham số sau tên chương trình): in `Usage: ...` ra `stderr`, **không** kết nối,
  thoát với mã `1`.

Bài này là bước khởi động cho `tcp-client-stdin`: ở đó phần dữ liệu gửi đi không còn lấy từ `argv[3]` mà từ `read(STDIN_FILENO, ...)`.

## Ràng buộc
- `<thông điệp>` là một tham số duy nhất (có thể chứa dấu cách và ký tự đặc biệt, có thể **rỗng**), dài tới 50 000 ký tự:
  đừng dùng bộ đệm cố định nhỏ để ghép `thông điệp + "\n"`.

## Ví dụ

```
./tcp_client 127.0.0.1 5000 "xin chao"   →   server nhận "xin chao\n", client thoát mã 0
./tcp_client 127.0.0.1 5000 ""           →   server nhận "\n"
./tcp_client 127.0.0.1                   →   stderr: Usage ..., mã thoát 1
```

## Gợi ý
- Khung như `tcp_client.c`: `socket` → điền `sockaddr_in` bằng `inet_addr(argv[1])` và `htons(atoi(argv[2]))` → `connect`
  (kiểm tra kết quả).
- Độ dài thông điệp là `strlen(argv[3])` (tham số dòng lệnh **là** xâu C nên dùng được `strlen`). Gọi `send` hai lần: một
  lần với `argv[3]`, một lần với `"\n"`. TCP là luồng byte nên server không phân biệt được với một lần gửi.
- `send` với độ dài `0` (thông điệp rỗng) là hợp lệ.
