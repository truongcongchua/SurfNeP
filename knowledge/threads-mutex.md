---
title: "Server đa luồng (pthread) & mutex"
chapter: 3
ref: "Lecture notes §3.4 (tr.71); L4-MultiThreading/pthread_chatroom.c"
---

## Tóm tắt
Mỗi client một **luồng**. Các luồng **chia sẻ** bộ nhớ nên chia sẻ dữ liệu dễ, nhưng phải **khoá** khi nhiều luồng cùng ghi.

```c
#include <pthread.h>        // biên dịch: gcc ... -pthread

void *serve(void *arg) {
    int c = *(int *)arg;
    free(arg);
    /* phục vụ client c */
    close(c);
    return NULL;
}

for (;;) {
    int *c = malloc(sizeof *c);              // cấp phát riêng cho mỗi luồng!
    *c = accept(s, NULL, NULL);
    pthread_t t;
    pthread_create(&t, NULL, serve, c);
    pthread_detach(t);                       // không cần join, tự giải phóng khi xong
}
```

## Mutex bảo vệ dữ liệu chung
```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

pthread_mutex_lock(&lock);
/* đọc/ghi bảng client, bảng key-value... */
pthread_mutex_unlock(&lock);
```
Giữ khoá **càng ngắn càng tốt**; không giữ khoá khi gọi `recv` (có thể chặn vô hạn) hay `send` tới client chậm.

## Bẫy thường gặp
- **Truyền `&c` của biến cục bộ** trong vòng `while`: vòng sau ghi đè giá trị trước khi luồng kịp đọc (race condition). Phải `malloc` cho mỗi luồng, hoặc ép `(intptr_t)`.
- Quên `pthread_detach` → luồng đã xong vẫn chiếm tài nguyên (giống zombie).
- Quên `-pthread` khi biên dịch → lỗi liên kết `undefined reference to pthread_create`.
- Quên mở khoá ở nhánh `return`/`break` sớm → **deadlock**.
- Hai luồng cùng `close` một fd, hoặc một luồng `close` fd còn đang nằm trong danh sách client.
- Dùng hàm không an toàn luồng (`strtok`, `inet_ntoa`, `gethostbyname`) → dùng `strtok_r`, `inet_ntop`, `getaddrinfo`.
- Số client giới hạn N: kiểm tra và tăng bộ đếm **trong cùng một lần giữ khoá**.
