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

## Kiến thức nền
Lecture notes §3.1; code mẫu `non_blocking_server.c`. Sau bài này, hãy so sánh với *select-echo*
để thấy vì sao cần cơ chế ghép kênh.
