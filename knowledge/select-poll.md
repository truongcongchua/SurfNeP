---
title: "Ghép kênh I/O: select và poll"
chapter: 3
ref: "Lecture notes §3.5 (tr.84); L5-IOMultiplexing"
---

## Ý tưởng
Một tiến trình, một luồng, nhưng **hệ điều hành báo** fd nào sẵn sàng đọc. Không bận chờ, không cần khoá.

## `select`
```c
fd_set master, rd;
FD_ZERO(&master);
FD_SET(listen_fd, &master);
int maxfd = listen_fd;

for (;;) {
    rd = master;                                   // select SỬA tập đầu vào → luôn dùng bản sao
    if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) { if (errno == EINTR) continue; break; }

    if (FD_ISSET(listen_fd, &rd)) {
        int c = accept(listen_fd, NULL, NULL);
        FD_SET(c, &master);
        if (c > maxfd) maxfd = c;
    }
    for (int fd = 0; fd <= maxfd; fd++) {
        if (fd == listen_fd || !FD_ISSET(fd, &rd)) continue;
        ssize_t n = recv(fd, buf, sizeof buf, 0);
        if (n <= 0) { close(fd); FD_CLR(fd, &master); }
        else        { /* xử lý */ }
    }
}
```
- Tham số đầu là **`maxfd + 1`**, không phải số lượng fd.
- Giới hạn `FD_SETSIZE` (thường 1024).

## `poll`
```c
struct pollfd fds[MAX];
fds[0].fd = listen_fd; fds[0].events = POLLIN;
int nfds = 1;
poll(fds, nfds, -1);                                // -1 = chờ vô hạn
for (int i = 0; i < nfds; i++)
    if (fds[i].revents & (POLLIN | POLLHUP | POLLERR)) { /* ... */ }
```
`poll` không phải tính `maxfd`, không bị `FD_SETSIZE`, và không sửa mảng `events` (chỉ ghi `revents`).

| | select | poll |
|---|---|---|
| Truyền | 3 `fd_set` + `maxfd+1` | mảng `struct pollfd` |
| Tập đầu vào bị sửa? | **có** (phải sao lưu) | không |
| Giới hạn | `FD_SETSIZE` | số phần tử mảng |

## Giới hạn của mô hình
Một lệnh chạy lâu (`sleep`, `system()`, đọc tệp lớn) trong vòng lặp sẽ **chặn mọi client khác**.

## Bẫy thường gặp
- Quên sao lưu `fd_set` (dùng `master` trực tiếp) → sau lần đầu mất hết fd.
- Truyền `maxfd` thay vì `maxfd + 1`.
- Không cập nhật `maxfd` khi nhận client mới.
- Không `FD_CLR` (hoặc không xoá khỏi mảng `pollfd`) sau khi đóng fd → `select` báo lỗi `EBADF`.
- Chỉ xử lý **một** fd sẵn sàng rồi quay lại `select` (vẫn đúng nhưng chậm); hoặc ngược lại, dùng nhầm `rd` đã bị sửa.
- Dữ liệu một client chia nhiều mảnh → cần **bộ đệm riêng cho từng client** để ghép dòng.
