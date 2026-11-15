# select() echo server

Viết echo server `./server <cổng>` giống bài *tcp-echo*: gửi trả nguyên vẹn mọi byte nhận được.
Khác biệt là server phải phục vụ **đồng thời** nhiều client (tối thiểu 50) trong **một tiến trình,
một luồng**, bằng **`select()`**.

**Không được dùng:** `fork`, `pthread`, `poll`, `epoll`. Bộ chấm kiểm tra điều này (verdict `CV`).

## Bộ chấm kiểm tra
- Client A kết nối rồi im lặng thì client B vẫn được phục vụ ngay (nếu không: `BLOCKED`).
- 20–50 client gửi xen kẽ.
- Một client ngắt kết nối không ảnh hưởng client khác.

## Kiến thức nền
Lecture notes §3.5: `fd_set` bị `select` **ghi đè**, nên phải dựng lại mỗi vòng lặp; tham số đầu
là `maxfd + 1`; khi `recv` trả về 0 thì `close` và bỏ fd khỏi danh sách.
