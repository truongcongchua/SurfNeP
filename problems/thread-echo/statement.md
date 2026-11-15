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

## Kiến thức nền
Lecture notes §3.4; code mẫu `pthread_server.c`.
