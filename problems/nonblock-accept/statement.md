# Server non-blocking không dùng select

Viết echo server `./server <cổng>` giống bài *tcp-echo*, phục vụ **đồng thời** tối thiểu 50 client
trong một tiến trình, một luồng, chỉ bằng **socket non-blocking**: đặt chế độ non-blocking bằng
`ioctl(fd, FIONBIO, ...)` hoặc `fcntl(fd, F_SETFL, O_NONBLOCK)` rồi **liên tục thử** `accept`/`recv`.

**Không được dùng:** `select`, `poll`, `epoll`, `fork`, `pthread`.

## Yêu cầu
- Phân biệt ba kết quả của `recv` trên socket non-blocking:
  `> 0` có dữ liệu; `0` client đóng; `-1` với `errno == EAGAIN/EWOULDBLOCK` **chưa có dữ liệu**
  (không phải lỗi!). Lỗi khác thì đóng client.
- Vòng lặp "thử liên tục" ăn 100% CPU. Hãy `usleep(1000)` khi một vòng không có việc gì.

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể đóng **đột ngột** (RST) khi server còn đang gửi: server không được chết vì `SIGPIPE`
  (dùng `MSG_NOSIGNAL` hoặc `signal(SIGPIPE, SIG_IGN)`, và kiểm tra giá trị trả về của `send`).
- Client có thể `shutdown(SHUT_WR)`: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc, gửi xen kẽ theo thứ tự ngẫu nhiên; client im lặng không được làm treo client khác.
- `send` trên socket non-blocking có thể trả `EAGAIN` khi bộ đệm gửi đầy: phải gửi lại phần còn lại.

## Kiến thức nền
Lecture notes §3.1; code mẫu `non_blocking_server.c`. Sau bài này, hãy so sánh với *select-echo*
để thấy vì sao cần cơ chế ghép kênh.
