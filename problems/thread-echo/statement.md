# Pthread echo server

Viết echo server `./server <cổng>` giống bài *tcp-echo* nhưng phục vụ **đồng thời** nhiều client
bằng **đa luồng**: mỗi client một luồng tạo bằng `pthread_create`.

**Không được dùng:** `fork`, `select`, `poll`, `epoll`.

## Bẫy kinh điển
```c
int client = accept(...);
pthread_create(&tid, NULL, worker, &client);   // SAI: mọi luồng trỏ tới cùng một biến
```
Vòng lặp tiếp theo ghi đè `client` trước khi luồng kịp đọc (code mẫu `pthread_server.c` mắc đúng lỗi
này). Hãy `malloc` một ô nhớ `int` riêng cho mỗi luồng, luồng đọc xong thì `free`. Nhớ `pthread_detach`
để luồng tự giải phóng tài nguyên khi kết thúc.

## Bài khởi động
Nếu chưa quen `pthread_create`, làm hai bài này trước. Mỗi bài luyện đúng một phần của bài này và dễ hơn nó:

| Bài | Luyện | Dùng lại ở bài này |
|---|---|---|
| `thread-args` (stdio, không có mạng) | Hàm luồng `void *f(void *)`, `malloc` một ô nhớ riêng cho mỗi luồng rồi `free` trong luồng, vì sao không được truyền `&i` | Cách đưa `fd` cho luồng |
| `thread-slow-hello` (server, không có `recv`) | Vòng `accept` → `pthread_create` → `pthread_detach`, luồng tự `close(fd)`, nhiều client chờ cùng lúc | Khung server đa luồng. Phần còn lại ở bài này là vòng `recv`/`send` đã làm ở `tcp-echo` |

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể ngừng gửi (`shutdown`) rồi chờ đọc: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc. Một client không đọc phản hồi không được làm treo client khác.

## Kiến thức nền
Lecture notes §3.4; code mẫu `pthread_server.c`.
