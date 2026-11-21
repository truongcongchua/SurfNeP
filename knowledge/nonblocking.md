---
title: "Socket non-blocking"
chapter: 3
ref: "Lecture notes §3.1 (tr.48); L1-NonBlocking/non_blocking_server.c"
---

## Hiểu nhanh
Mặc định `accept`, `recv` là **blocking** (chặn): gọi `recv` mà chưa có dữ liệu thì chương trình **đứng im chờ**, giống bạn đứng trước cửa chờ bưu tá. Trong lúc đó không làm được gì khác, kể cả phục vụ client khác.

**Non-blocking** (không chặn): gọi `recv` mà chưa có dữ liệu thì hàm **trả về ngay** kèm thông báo "chưa có gì", giống liếc qua hộp thư rồi đi làm việc khác. Nhờ vậy một vòng lặp có thể lần lượt hỏi nhiều client.

## Bật chế độ non-blocking
```c
#include <fcntl.h>

void set_nonblock(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);         // lấy cờ hiện tại
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);    // thêm cờ O_NONBLOCK
}
```

## Đọc kết quả `recv` khi non-blocking
Có thêm một trường hợp: trả `-1` nhưng **không phải lỗi**.

| Kết quả | Nghĩa là | Nên làm |
|---|---|---|
| `> 0` | có dữ liệu | xử lý |
| `0` | client đã đóng | `close(fd)`, bỏ khỏi danh sách |
| `-1` và `errno == EAGAIN` hoặc `EWOULDBLOCK` | **chưa có dữ liệu** | bỏ qua, sang client khác |
| `-1` và `errno` khác | lỗi thật | đóng client |

`errno` là biến toàn cục (khai báo trong `<errno.h>`) chứa mã lỗi của lần gọi hệ thống **gần nhất**.

## Mẫu: một vòng lặp phục vụ nhiều client
```c
#include <errno.h>

set_nonblock(listen_fd);                       // socket nghe cũng phải non-blocking
int clients[MAX]; int nc = 0;

for (;;) {
    // 1. Có khách mới không? (không có thì accept trả -1 ngay, không chờ)
    int c = accept(listen_fd, NULL, NULL);
    if (c >= 0) { set_nonblock(c); clients[nc++] = c; }

    // 2. Hỏi lần lượt từng client
    for (int i = 0; i < nc; i++) {
        char buf[1024];
        ssize_t n = recv(clients[i], buf, sizeof buf, 0);
        if (n > 0) {
            send(clients[i], buf, n, 0);
        } else if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK)) {
            close(clients[i]);                 // đóng rồi xoá khỏi mảng
            clients[i] = clients[--nc];        // đưa phần tử cuối vào chỗ trống
            i--;                               // xét lại vị trí i
        }
        // còn lại: EAGAIN → chưa có gì, bỏ qua
    }
    usleep(1000);                              // nghỉ 1ms cho CPU đỡ quay không
}
```

## Nhược điểm
Vòng lặp trên phải **hỏi tất cả client liên tục**, kể cả khi không ai gửi gì: tốn CPU (gọi là **bận chờ**, busy-wait). Thêm `usleep` thì đỡ tốn nhưng phản hồi chậm hơn. Cách tốt hơn là để hệ điều hành **báo** client nào có dữ liệu: đó là `select`/`poll` (xem thẻ *select và poll*).

## Lỗi hay gặp
- **Client bị đóng vô cớ.** Coi `EAGAIN` là lỗi. `EAGAIN` chỉ nghĩa là "chưa có dữ liệu".
- **Cả server vẫn bị treo.** Quên đặt non-blocking cho **socket nghe**, nên `accept` vẫn đứng chờ.
- **Xét `errno` ra kết quả lạ.** Gọi hàm khác (vd. `printf`) giữa `recv` và chỗ kiểm tra `errno`, `errno` bị ghi đè. Kiểm tra **ngay sau** `recv`.
- **CPU 100%.** Không có `usleep` trong vòng lặp.
- `send` non-blocking cũng có thể gửi thiếu hoặc trả `EAGAIN` khi bộ đệm gửi đầy.
