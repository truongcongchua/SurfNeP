---
title: "Vòng đời socket TCP (server & client)"
chapter: 2
ref: "Lecture notes §2.3 (tr.22)"
---

## Trình tự
**Server:** `socket` → `bind` → `listen` → `accept` (lặp) → `recv`/`send` → `close`
**Client:** `socket` → `connect` → `send`/`recv` → `close`

```c
int s = socket(AF_INET, SOCK_STREAM, 0);
int yes = 1;
setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);   // chạy lại server không bị "Address already in use"
struct sockaddr_in a = {0};
a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_ANY);
bind(s, (struct sockaddr *)&a, sizeof a);
listen(s, 16);

for (;;) {
    struct sockaddr_in c; socklen_t cl = sizeof c;
    int fd = accept(s, (struct sockaddr *)&c, &cl);   // trả về socket MỚI cho client này
    char buf[1024]; ssize_t n;
    while ((n = recv(fd, buf, sizeof buf, 0)) > 0) send(fd, buf, n, 0);
    close(fd);
}
```

## Hai loại socket
- **Socket nghe** (`s`): chỉ để `accept`, không đọc/ghi dữ liệu.
- **Socket kết nối** (`fd` do `accept` trả về): một socket cho **mỗi** client.

## Giá trị trả về của `recv`
| Giá trị | Ý nghĩa |
|---|---|
| `> 0` | số byte nhận được (có thể **ít hơn** yêu cầu) |
| `0` | đối phương đã **đóng** kết nối (EOF) |
| `-1` | lỗi, xem `errno` (`EINTR` thì thử lại) |

## Bẫy thường gặp
- Quên `SO_REUSEADDR` → chạy lại server báo `bind: Address already in use`.
- Nhầm socket nghe với socket kết nối khi `recv`/`close`.
- Không kiểm tra `recv` trả `0` → vòng lặp quay vô hạn khi client đã thoát.
- `send` cũng có thể gửi ít hơn yêu cầu; với dữ liệu lớn phải lặp cho đến hết.
- Quên `close(fd)` → rò rỉ descriptor, server chết sau vài trăm client.
- Dùng `strlen` thay vì số byte `n` thực nhận khi gửi lại (dữ liệu có thể chứa `\0`).
