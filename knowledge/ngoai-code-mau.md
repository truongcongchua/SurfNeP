---
title: "Hàm mạng ngoài code mẫu (tùy chọn, cho BTL)"
chapter: 4
ref: "Unix Network Programming, Vol. 1 (Stevens); man 2 send / signal / poll / fcntl / shutdown; man 3 inet_pton"
---

> **Không bắt buộc, không có trong đề thi giữa kỳ.** Lời giải mẫu của mọi bài chỉ dùng những gì có trong code mẫu của
> thầy. Thẻ này giải thích vài hàm ngoài code mẫu mà **có thể làm bài tập lớn tốt hơn**, xếp từ đáng dùng nhất. Bài nào
> cho phép dùng thêm sẽ ghi rõ ở mục "Được phép dùng thêm".

## 1. `SIGPIPE`: client rớt mạng làm sập cả server (đáng dùng nhất)
Khi `send` vào một kết nối mà phía bên kia **đã đóng**, hệ điều hành gửi tín hiệu `SIGPIPE` cho tiến trình, và mặc định
tín hiệu này **giết tiến trình**. Trong BTL server liên tục đẩy dữ liệu cho client (phản hồi, vé điện tử, thông báo), nên chỉ cần
một client rớt mạng là cả server chết và mọi người mất ghế đang giữ.

Hai cách tắt (chọn một):
```c
#include <signal.h>
signal(SIGPIPE, SIG_IGN);                    // 1. một lần ở đầu main: bỏ qua tín hiệu

send(fd, buf, len, MSG_NOSIGNAL);            // 2. từng lần gửi: không phát sinh SIGPIPE cho lần này
```
Sau đó `send` chỉ trả `-1` (lỗi `EPIPE`) thay vì giết server. `signal()` đã có trong code mẫu (`ex4.c`–`ex6.c`); chỉ hằng
`SIGPIPE` và `SIG_IGN` là mới. Khi `send` trả `-1`, coi như client đã chết: bỏ nó khỏi danh sách và `close`.

## 2. `errno` và `strerror`: biết *vì sao* lỗi
```c
#include <errno.h>
#include <string.h>
if (send(fd, buf, len, 0) < 0)
    fprintf(log, "send %d: %s\n", fd, strerror(errno));   // "Broken pipe", "Connection reset by peer"...
```
Hữu ích khi ghi log của BTL: phân biệt client đóng bình thường (`recv` trả `0`) với lỗi thật (`ECONNRESET`, `EPIPE`).
`perror("send")` làm gần như việc tương tự và đã có trong code mẫu.

## 3. `inet_pton` / `inet_ntop`: chuyển địa chỉ có kiểm tra lỗi
```c
struct in_addr a;
if (inet_pton(AF_INET, "192.168.1.5", &a) != 1) puts("địa chỉ sai");   // 1 = hợp lệ, 0 = sai định dạng
char s[INET_ADDRSTRLEN];
inet_ntop(AF_INET, &a, s, sizeof s);                                    // nhị phân -> chuỗi
```
Thay cho `inet_addr`/`inet_ntoa` của code mẫu: báo lỗi rõ ràng (`inet_addr` trả `INADDR_NONE` trùng với địa chỉ hợp lệ
`255.255.255.255`), `inet_ntop` an toàn khi gọi nhiều lần (`inet_ntoa` dùng bộ đệm tĩnh nên không dùng chung được giữa các
luồng), và hỗ trợ IPv6 (`AF_INET6`). Với BTL chạy IPv4 nội bộ, khác biệt nhỏ.

## 4. `poll`: thay cho `select`
```c
#include <poll.h>
struct pollfd fds[64];
fds[0].fd = listener; fds[0].events = POLLIN;
...
int r = poll(fds, nfds, -1);                 // -1 = chờ mãi; số ms nếu muốn timeout
for (int i = 0; i < nfds; i++)
    if (fds[i].revents & POLLIN) { /* fd này đọc được */ }
```
So với `select`: không phải dựng lại tập `fd_set` mỗi vòng, không bị giới hạn `FD_SETSIZE` (1024 fd), `fd` âm bị bỏ qua. Với
vài chục client như BTL thì `select` vẫn đủ nên **không cần chuyển**.

## 5. `fcntl(fd, F_SETFL, O_NONBLOCK)`: chế độ không chặn
```c
#include <fcntl.h>
fcntl(fd, F_SETFL, fcntl(fd, F_GETFL, 0) | O_NONBLOCK);
```
Tương đương `ioctl(fd, FIONBIO, &on)` trong `non_blocking_server.c`, chỉ là cách viết theo chuẩn POSIX. Không thêm tính năng.

## 6. `shutdown(fd, SHUT_WR)`: đóng một chiều
Báo "tôi gửi xong" (đối phương `recv` được `0`) nhưng **vẫn nhận tiếp**. Cần khi dùng "đóng kết nối" để đánh dấu hết dữ liệu.
Giao thức FLY đếm trước số dòng/số byte và có `QUIT` nên không cần.

## Tóm tắt
| Hàm | Giúp BTL? | Dùng khi |
|---|---|---|
| `signal(SIGPIPE, SIG_IGN)` / `MSG_NOSIGNAL` | **Có**, nên dùng | server đẩy dữ liệu cho client bất kỳ lúc nào |
| `errno` + `strerror` | Có, nhỏ | ghi log lý do lỗi |
| `inet_pton` / `inet_ntop` | Ít | kiểm tra tham số IP chặt hơn, IPv6 |
| `poll` | Ít | quá 1000 client |
| `fcntl O_NONBLOCK` | Không thêm gì | thích cách viết POSIX |
| `shutdown` | Hầu như không | giao thức dùng "đóng" để báo hết dữ liệu |
