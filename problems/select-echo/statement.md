# Echo server dùng select

Viết echo server `./server <cổng>` giống bài *tcp-echo*: gửi trả nguyên vẹn mọi byte nhận được.
Khác biệt là server phải phục vụ **đồng thời** nhiều client (tối thiểu 50) trong **một tiến trình,
một luồng**, bằng **`select()`**.

**Không được dùng:** `fork`, `pthread`, `poll`, `epoll`. Bộ chấm kiểm tra điều này (verdict `CV`).

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể đóng **đột ngột** (RST) khi server còn đang gửi: server không được chết vì `SIGPIPE`
  (dùng `MSG_NOSIGNAL` hoặc `signal(SIGPIPE, SIG_IGN)`, và kiểm tra giá trị trả về của `send`).
- Client có thể `shutdown(SHUT_WR)`: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc, gửi xen kẽ theo thứ tự ngẫu nhiên; client im lặng không được làm treo client khác.

## Kiến thức nền
Lecture notes §3.5: `fd_set` bị `select` **ghi đè**, nên phải dựng lại mỗi vòng lặp; tham số đầu
là `maxfd + 1`; khi `recv` trả về 0 thì `close` và bỏ fd khỏi danh sách.
