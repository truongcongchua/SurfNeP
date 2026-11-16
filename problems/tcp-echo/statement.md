# TCP echo server

Viết server chạy bằng `./server <cổng>`. Server gửi trả **nguyên vẹn từng byte** nhận được từ
client (kể cả byte `0x00` và dữ liệu nhị phân), cho đến khi client đóng kết nối.

- Phục vụ **lần lượt** từng client là đủ (server lặp). Xong client này thì `accept` client tiếp theo.
- Server **không được thoát** khi một client ngắt kết nối.

## Ví dụ

```
client gửi: "xin chao\n"    →  server gửi lại: "xin chao\n"
client gửi 3 byte 00 FF 41  →  server gửi lại: 00 FF 41
```

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể đóng **đột ngột** (RST) khi server còn đang gửi: server không được chết vì `SIGPIPE`
  (dùng `MSG_NOSIGNAL` hoặc `signal(SIGPIPE, SIG_IGN)`, và kiểm tra giá trị trả về của `send`).
- Client có thể `shutdown(SHUT_WR)`: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).

## Bẫy thường gặp
- Dùng `strlen`/`printf("%s")` với dữ liệu nhận được: hỏng khi có byte `0x00`. Dùng **số byte
  `recv` trả về**.
- `send()` có thể gửi **ít hơn** số byte yêu cầu. Cần vòng lặp gửi cho đủ (viết hàm `send_all`).
- Không kiểm tra `recv() == 0` (client đóng) thì server rơi vào vòng lặp vô hạn.
