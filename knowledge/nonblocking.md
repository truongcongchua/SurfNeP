---
title: "Socket non-blocking"
chapter: 3
ref: "Lecture notes §3.1 (tr.48); L1-NonBlocking/non_blocking_server.c"
---

## Tóm tắt
Mặc định `accept`/`recv`/`send` là **blocking**: chương trình đứng chờ đến khi có việc. Socket **non-blocking** trả về ngay; nếu chưa có dữ liệu thì `-1` với `errno == EAGAIN` (hoặc `EWOULDBLOCK`), **không phải lỗi**.

```c
#include <fcntl.h>
int fl = fcntl(fd, F_GETFL, 0);
fcntl(fd, F_SETFL, fl | O_NONBLOCK);       // hoặc ioctl(fd, FIONBIO, &on)
```

## Ba kết quả của `recv`
| Kết quả | Hành động |
|---|---|
| `> 0` | xử lý dữ liệu |
| `0` | client đóng → `close` và bỏ khỏi danh sách |
| `-1`, `errno == EAGAIN/EWOULDBLOCK` | chưa có dữ liệu → bỏ qua, thử client khác |
| `-1`, lỗi khác | lỗi thật → đóng client |

## Mô hình "polling" một luồng
```c
for (;;) {
    int c = accept(s, NULL, NULL);          // s cũng non-blocking
    if (c >= 0) { set_nonblock(c); add_client(c); }
    for (each client fd) {
        n = recv(fd, buf, sizeof buf, 0);
        if (n > 0) send(fd, buf, n, 0);
        else if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK)) drop(fd);
    }
    usleep(1000);                            // nhường CPU nếu cả vòng không có việc
}
```

## Hạn chế
Vòng lặp **bận chờ** (busy-wait) ăn 100% CPU nếu không `usleep`, và mỗi vòng phải hỏi **tất cả** client dù không ai gửi gì. Đó là lý do cần `select`/`poll` (hệ điều hành báo fd nào sẵn sàng).

## Bẫy thường gặp
- Coi `EAGAIN` là lỗi và đóng client.
- Quên đặt non-blocking cho **socket nghe** → `accept` vẫn chặn cả vòng lặp.
- Quên kiểm tra `errno` ngay sau `recv` (bị lệnh khác ghi đè).
- Không `usleep` → CPU 100%.
- `send` non-blocking cũng có thể gửi thiếu hoặc `EAGAIN` khi bộ đệm đầy.
