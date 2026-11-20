# Pthread echo server

Viết echo server `./server <cổng>` giống bài *tcp-echo* nhưng phục vụ **đồng thời** nhiều client
bằng **đa luồng**: mỗi client một luồng tạo bằng `pthread_create`.

**Không được dùng:** `fork`, `select`, `poll`, `epoll`.

## Bẫy kinh điển
```c
int client = accept(...);
pthread_create(&tid, NULL, worker, &client);   // SAI: mọi luồng trỏ tới cùng một biến
```
Vòng lặp tiếp theo ghi đè `client` trước khi luồng kịp đọc. Hãy `malloc` một ô nhớ riêng cho mỗi
luồng (hoặc truyền giá trị qua `(void *)(intptr_t)client`). Nhớ `pthread_detach` để luồng tự giải
phóng tài nguyên khi kết thúc.

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể đóng **đột ngột** (RST) khi server còn đang gửi: server không được chết vì `SIGPIPE`
  (dùng `MSG_NOSIGNAL` hoặc `signal(SIGPIPE, SIG_IGN)`, và kiểm tra giá trị trả về của `send`).
- Client có thể `shutdown(SHUT_WR)`: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc. Một client không đọc phản hồi không được làm treo client khác.

## Kiến thức nền
Lecture notes §3.4; code mẫu `pthread_server.c`.
