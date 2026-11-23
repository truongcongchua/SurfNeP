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

## Nên làm trước (luyện từng hàm)
Bài này dùng cùng lúc `socket`, `bind`, `listen`, `accept`, `recv`, `send`, `close`. Nếu còn thấy lạ, làm lần lượt ba bài khởi động ngắn sau (mỗi bài thêm đúng một thứ):

| Thứ tự | Bài | Luyện |
|---|---|---|
| 1 | *tcp-accept-close* | `socket` → `bind` → `listen` → `accept` → `close` (điền `sockaddr_in`, `htons`, hai loại socket) |
| 2 | *tcp-hello-loop* | vòng lặp `accept`, `send`, `close(client)` cho từng client (chưa cần `recv`) |
| 3 | *tcp-echo-once* | `recv` rồi `send` đúng số byte nhận được, đúng như `tcp_server.c` |

Sau bài 3, bài *tcp-echo* này chỉ thêm đúng **hai vòng lặp**: vòng ngoài `accept` để phục vụ lần lượt nhiều client, vòng trong `recv` → `send` cho tới khi client đóng.

## Các hàm cần dùng

| Hàm | Làm gì | Trả về |
|---|---|---|
| `socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)` | tạo socket nghe (`listener`) | fd, `-1` nếu lỗi |
| `bind(listener, (struct sockaddr*)&addr, sizeof(addr))` | gán IP + cổng (`htons(atoi(argv[1]))`, `INADDR_ANY`) | `0`, `-1` nếu lỗi |
| `listen(listener, 5)` | bắt đầu nghe | `0`, `-1` nếu lỗi |
| `accept(listener, NULL, NULL)` | chờ client, trả về socket **riêng** của client đó | fd mới, `-1` nếu lỗi |
| `recv(client, buffer, sizeof(buffer), 0)` | nhận dữ liệu | số byte; **`0` = client đóng**; `-1` lỗi |
| `send(client, buffer, bytes_received, 0)` | gửi lại đúng số byte nhận được | số byte gửi, `-1` lỗi |
| `close(client)` | đóng socket của client (xong mỗi client) | |

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể ngừng gửi (`shutdown`) rồi chờ đọc: server phải gửi trả **hết** rồi mới đóng.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).

## Bẫy thường gặp
- Dùng `strlen`/`printf("%s")` với dữ liệu nhận được: hỏng khi có byte `0x00`. Dùng **số byte
  `recv` trả về** làm độ dài khi `send` lại.
- Chỉ gọi `recv` một lần như `tcp_server.c`: dữ liệu lớn đến qua **nhiều** lần `recv`, phải lặp
  `recv` → `send` cho tới khi `recv` trả về `0` (client đóng).
- Không kiểm tra `recv() <= 0` thì server rơi vào vòng lặp vô hạn khi client đóng.

## Kiến thức nền
Code mẫu `2-Chap2/tcp_server.c` (thêm hai vòng lặp: `accept` và `recv`/`send`).
