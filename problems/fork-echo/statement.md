# Forking echo server

Viết echo server `./server <cổng>` giống bài *tcp-echo* nhưng phục vụ **đồng thời** nhiều client
bằng kỹ thuật **đa tiến trình**: mỗi client được xử lý bởi một tiến trình con tạo bằng `fork()`.

**Không được dùng:** `pthread`, `select`, `poll`, `epoll`.

## Yêu cầu thêm
- Tiến trình **cha** đóng socket của client sau khi `fork`; tiến trình **con** đóng socket lắng nghe.
- Khi tiến trình con kết thúc, cha phải **thu dọn** nó (`waitpid`), nếu không sẽ tích tụ **zombie**.
  Bộ chấm đếm số zombie sau khi 10 client lần lượt rời đi. Làm như `forking_server.c`:
  `signal(SIGCHLD, signal_handler)` với handler gọi `waitpid(-1, NULL, WNOHANG)` **trong vòng `while`**.

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể ngừng gửi (`shutdown`) rồi chờ đọc: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc; 30 tiến trình con có thể kết thúc **cùng một lúc** (nhiều `SIGCHLD` bị gộp làm một)
  và bộ chấm đếm zombie; tối đa 128 tiến trình trong máy chấm.
- Một client không đọc phản hồi không được làm treo client khác.

## Kiến thức nền
Lecture notes §3.3; code mẫu `forking_server.c`, `preforking_server.c`.
