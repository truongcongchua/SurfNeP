---
title: "Ghép kênh I/O: select và poll"
chapter: 3
ref: "Lecture notes §3.5 (tr.84); L5-IOMultiplexing"
---

## Hiểu nhanh
Bạn là nhân viên phục vụ một mình cho nhiều bàn. Thay vì chạy qua hỏi từng bàn liên tục (cách non-blocking), bạn **đứng chờ ở quầy**, bàn nào bấm chuông thì mới tới bàn đó.

`select`/`poll` chính là cái chuông: bạn đưa cho hệ điều hành **danh sách socket** cần theo dõi, rồi chương trình ngủ cho đến khi **có ít nhất một socket sẵn sàng** (có dữ liệu để đọc, hoặc có client mới). Hàm trả về cho biết socket nào sẵn sàng.

Lợi ích: một chương trình, một luồng, phục vụ nhiều client, không tốn CPU vô ích, không cần khoá (mutex) vì chỉ có một luồng.

"Socket nghe sẵn sàng" nghĩa là có client mới đang chờ → gọi `accept` sẽ không bị chặn.

## `select`: từng bước
`fd_set` là một **tập hợp các số fd**. Có 4 macro thao tác với nó:

| Macro | Việc làm |
|---|---|
| `FD_ZERO(&set)` | làm rỗng tập |
| `FD_SET(fd, &set)` | thêm `fd` vào tập |
| `FD_CLR(fd, &set)` | bỏ `fd` khỏi tập |
| `FD_ISSET(fd, &set)` | `fd` có trong tập không? |

**Điểm quan trọng:** `select` **sửa** tập bạn đưa vào, chỉ để lại những fd sẵn sàng. Vì vậy giữ một tập gốc `master` (mọi fd đang theo dõi) và mỗi vòng **sao chép** sang `rd` rồi đưa `rd` cho `select`.

```c
#include <sys/select.h>

fd_set master, rd;
FD_ZERO(&master);
FD_SET(listen_fd, &master);            // ban đầu chỉ theo dõi socket nghe
int maxfd = listen_fd;                 // fd lớn nhất đang theo dõi

for (;;) {
    rd = master;                       // sao chép, vì select sẽ sửa rd
    if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) {
        if (errno == EINTR) continue;  // bị tín hiệu ngắt: thử lại
        perror("select"); break;
    }

    // 1. Socket nghe sẵn sàng → có client mới
    if (FD_ISSET(listen_fd, &rd)) {
        int c = accept(listen_fd, NULL, NULL);
        if (c >= 0) {
            FD_SET(c, &master);        // từ giờ theo dõi luôn client này
            if (c > maxfd) maxfd = c;
        }
    }

    // 2. Client nào có dữ liệu?
    for (int fd = 0; fd <= maxfd; fd++) {
        if (fd == listen_fd || !FD_ISSET(fd, &rd)) continue;
        char buf[1024];
        ssize_t n = recv(fd, buf, sizeof buf, 0);
        if (n <= 0) {                  // client đóng hoặc lỗi
            close(fd);
            FD_CLR(fd, &master);       // thôi theo dõi
        } else {
            /* xử lý n byte trong buf */
        }
    }
}
```
- Tham số đầu của `select` là **`maxfd + 1`** (fd lớn nhất cộng 1), **không phải** số lượng fd.
- Ba tham số tiếp theo: tập theo dõi **đọc**, **ghi**, **ngoại lệ**. Thường chỉ cần đọc, hai cái kia để `NULL`.
- Tham số cuối là thời gian chờ tối đa; `NULL` = chờ mãi.
- `select` chỉ theo dõi được fd nhỏ hơn `FD_SETSIZE` (thường 1024).

## `poll`: cùng ý tưởng, dùng mảng
Mỗi phần tử `struct pollfd` gồm: `fd` (socket nào), `events` (muốn theo dõi gì, thường `POLLIN` = có dữ liệu đọc), `revents` (hệ điều hành ghi kết quả vào đây).
```c
#include <poll.h>

struct pollfd fds[MAX];
int nfds = 0;
fds[nfds].fd = listen_fd; fds[nfds].events = POLLIN; nfds++;

for (;;) {
    poll(fds, nfds, -1);                          // -1 = chờ mãi
    for (int i = 0; i < nfds; i++) {
        if (!(fds[i].revents & (POLLIN | POLLHUP | POLLERR))) continue;
        if (fds[i].fd == listen_fd) {
            int c = accept(listen_fd, NULL, NULL);
            fds[nfds].fd = c; fds[nfds].events = POLLIN; fds[nfds].revents = 0; nfds++;
        } else {
            ssize_t n = recv(fds[i].fd, buf, sizeof buf, 0);
            if (n <= 0) {
                close(fds[i].fd);
                fds[i] = fds[--nfds];             // phần tử cuối vào chỗ trống
                i--;
            } else { /* xử lý */ }
        }
    }
}
```

| | `select` | `poll` |
|---|---|---|
| Danh sách theo dõi | `fd_set` + `maxfd + 1` | mảng `struct pollfd` |
| Có sửa danh sách đầu vào? | **có**, phải sao chép mỗi vòng | không (chỉ ghi `revents`) |
| Giới hạn số fd | `FD_SETSIZE` (~1024) | kích thước mảng bạn cấp |

## Hạn chế cần biết
Chỉ có một luồng, nên nếu đang xử lý một client mà làm việc **lâu** (`sleep`, `system()`, đọc tệp lớn), mọi client khác phải chờ.

## Lỗi hay gặp
- **Sau vòng đầu không nhận được gì nữa.** Đưa thẳng `master` cho `select` nên bị sửa mất. Sửa: `rd = master;` mỗi vòng.
- **Client mới không bao giờ được phục vụ.** Truyền `maxfd` thay vì `maxfd + 1`, hoặc quên cập nhật `maxfd` khi `accept`.
- **`select` báo lỗi `Bad file descriptor`.** Đã `close(fd)` nhưng quên `FD_CLR` (hoặc quên xoá khỏi mảng `pollfd`).
- **Dòng lệnh bị trộn giữa các client.** Dùng chung một bộ đệm. Mỗi client cần **bộ đệm riêng** để ghép dòng (xem thẻ *Quản lý nhiều client*).
