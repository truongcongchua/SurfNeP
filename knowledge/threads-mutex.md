---
title: "Server đa luồng (pthread) & mutex"
chapter: 3
ref: "Lecture notes §3.4 (tr.71); L4-MultiThreading/pthread_chatroom.c"
---

## Hiểu nhanh
**Luồng** (thread) là một "dòng chạy" trong cùng một chương trình. Server đa luồng giống **một văn phòng nhiều nhân viên**: mỗi khách có một nhân viên riêng phục vụ, và mọi nhân viên **dùng chung** một tủ hồ sơ (bộ nhớ chung).

So với `fork` (mỗi nhân viên một văn phòng riêng): luồng chia sẻ dữ liệu rất dễ, nhưng hai người cùng sửa một tờ hồ sơ một lúc sẽ hỏng. Vì vậy cần **khoá** (mutex).

## Tạo một luồng cho mỗi client
```c
#include <pthread.h>        // biên dịch: gcc server.c -o server -pthread

void *serve(void *arg) {                     // hàm luồng: nhận void*, trả void*
    int c = *(int *)arg;                     // lấy số fd ra
    free(arg);                               // trả bộ nhớ đã malloc ở dưới
    /* ... recv / send với client c ... */
    close(c);
    return NULL;
}

for (;;) {
    int c = accept(listen_fd, NULL, NULL);
    if (c < 0) continue;

    int *pc = malloc(sizeof *pc);            // mỗi luồng một ô nhớ RIÊNG
    *pc = c;
    pthread_t t;
    pthread_create(&t, NULL, serve, pc);     // chạy serve(pc) ở luồng mới
    pthread_detach(t);                       // luồng xong tự dọn, không cần join
}
```

**Vì sao phải `malloc`?** Nếu truyền `&c` (địa chỉ biến `c` của vòng lặp): luồng mới chưa kịp đọc thì vòng lặp đã `accept` client sau và ghi đè `c`. Hai luồng phục vụ cùng một client, client kia bị bỏ rơi.

## Mutex: khoá khi dùng dữ liệu chung
Mutex giống **chìa khoá phòng duy nhất**: ai cầm chìa thì vào, người khác đứng chờ đến khi chìa được trả.
```c
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;   // biến toàn cục

pthread_mutex_lock(&lock);        // lấy chìa (chờ nếu người khác đang cầm)
nclients++;                       // đọc/sửa dữ liệu chung: mảng client, bảng key-value...
pthread_mutex_unlock(&lock);      // trả chìa
```
Quy tắc:
- **Mọi** chỗ đọc/sửa dữ liệu chung đều phải nằm giữa `lock` và `unlock`.
- Giữ khoá **càng ngắn càng tốt**. Không gọi `recv` khi đang giữ khoá (có thể chờ mãi, mọi luồng khác đứng theo).
- Kiểm tra rồi sửa phải nằm **trong cùng một lần khoá**, vd. "nếu chưa đủ N thì tăng bộ đếm".

## Lỗi hay gặp
- **Lỗi biên dịch `undefined reference to pthread_create`.** Thiếu cờ `-pthread`.
- **Hai luồng phục vụ cùng một client.** Truyền `&c` thay vì `malloc` riêng cho từng luồng.
- **Server treo cứng, không ai được phục vụ** (deadlock). Có nhánh `return`/`break` thoát ra mà **quên `unlock`**.
- **Dữ liệu chung bị sai lúc có lúc không.** Quên khoá ở một chỗ đọc/sửa. Lỗi kiểu này khó tái hiện vì phụ thuộc thời điểm.
- **Luồng xong vẫn chiếm tài nguyên.** Không `pthread_detach` (cũng không `pthread_join`).
- **Kết quả tách xâu bị lộn giữa các client.** `strtok` dùng chung trạng thái cho cả chương trình. Trong luồng dùng `strtok_r`; tương tự dùng `inet_ntop` thay `inet_ntoa`.
