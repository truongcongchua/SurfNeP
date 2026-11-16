## 1. Vòng đời socket

| | TCP server | TCP client | UDP |
|---|---|---|---|
| Tạo | `socket(AF_INET, SOCK_STREAM, 0)` | giống server | `socket(AF_INET, SOCK_DGRAM, 0)` |
| Gán địa chỉ | `bind` | (không cần) | server: `bind` |
| Chờ / nối | `listen` → `accept` (trả socket **mới**) | `connect` | (không có) |
| Gửi / nhận | `send` / `recv` | `send` / `recv` | `sendto` / `recvfrom` |
| Đóng | `close` | `close` | `close` |

## 2. Giá trị trả về cần nhớ

| Hàm | Kết quả |
|---|---|
| `recv` | `> 0` số byte (có thể ít hơn yêu cầu) · `0` đối phương đóng · `-1` lỗi (`EINTR` thử lại; non-blocking: `EAGAIN` = chưa có dữ liệu) |
| `recvfrom` (UDP) | `>= 0` độ dài datagram (`0` = datagram **rỗng**, không phải đóng) · `-1` lỗi |
| `send` | số byte gửi được (có thể ít hơn → vòng lặp `send_all`) |
| `inet_pton` | `1` hợp lệ · `0` xâu sai định dạng · `-1` họ địa chỉ không hỗ trợ |
| `getaddrinfo` | `0` thành công (kết quả là danh sách `ai_next`, nhớ `freeaddrinfo`) · khác `0` là lỗi |
| `select` | số fd sẵn sàng · `-1` lỗi (`EINTR`) |
| `fork` | `0` ở tiến trình con · `pid` ở cha · `-1` lỗi |

## 3. Byte order

| Hàm | Dùng cho |
|---|---|
| `htons` / `ntohs` | 16 bit: **cổng** |
| `htonl` / `ntohl` | 32 bit: IPv4, **độ dài** thông điệp |

Máy x86 là little-endian (`0x1234` lưu `34 12`); mạng là big-endian (`12 34`). Chuỗi ký tự không cần đổi.

## 4. TCP là luồng byte

- Một `send` **không** bằng một `recv`: có thể bị tách hoặc gộp.
- Đóng khung: ký tự kết thúc (`\n`, `\r\n\r\n`) · độ dài cố định · **độ dài tiền tố** (4 byte `htonl` + dữ liệu).
- Đọc dòng: bộ đệm lưu giữa các lần gọi → `memchr('\n')` → `memmove` phần dư.
- Tìm chuỗi: trên **bộ đệm tích luỹ**, không tìm riêng từng mảnh.
- UDP thì ngược lại: mỗi datagram là một thông điệp trọn vẹn (bộ đệm phải đủ lớn, tới 65507 byte).

## 5. So sánh mô hình phục vụ nhiều client

| Mô hình | Cách làm | Chia sẻ dữ liệu | Điểm cần nhớ / bẫy |
|---|---|---|---|
| Lặp (iterative) | `accept` → xong → `accept` | dễ | client chậm chặn tất cả |
| Non-blocking | `O_NONBLOCK`, thử liên tục | dễ | `EAGAIN` không phải lỗi; `usleep` kẻo ăn 100% CPU |
| `fork` | mỗi client một tiến trình | **không** (bộ nhớ riêng) | `SIGCHLD` + `waitpid(WNOHANG)` chống zombie; con đóng socket nghe, cha đóng socket client |
| `pthread` | mỗi client một luồng | có (cần **mutex**) | `malloc` tham số cho từng luồng; `pthread_detach` (không `join` ngay); `-pthread` |
| `select` | một luồng, tập `fd_set` | dễ, không cần khoá | sao lưu `fd_set`; `maxfd + 1`; `FD_CLR` khi đóng; lệnh chậm chặn tất cả |
| `poll` | một luồng, mảng `pollfd` | dễ | kiểm tra `revents`; không giới hạn 1024 |

## 6. Khung mã hay dùng

**Server TCP lặp**
```c
int s = socket(AF_INET, SOCK_STREAM, 0);
int yes = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
struct sockaddr_in a = {0};
a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_ANY);
bind(s, (struct sockaddr *)&a, sizeof a);
listen(s, 16);
for (;;) {
    int c = accept(s, NULL, NULL);
    /* phục vụ c */
    close(c);
}
```

**send_all / recv_all**
```c
int send_all(int fd, const void *p, size_t n) {
    size_t sent = 0;
    while (sent < n) {
        ssize_t r = send(fd, (const char *)p + sent, n - sent, MSG_NOSIGNAL);
        if (r <= 0) return -1;
        sent += r;
    }
    return 0;
}
int recv_all(int fd, void *p, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t r = recv(fd, (char *)p + got, n - got, 0);
        if (r <= 0) return -1;
        got += r;
    }
    return 0;
}
```

**Chống zombie (fork)**
```c
void reap(int sig) { while (waitpid(-1, NULL, WNOHANG) > 0); }
signal(SIGCHLD, reap);
```

**Vòng lặp select**
```c
fd_set master, rd; FD_ZERO(&master); FD_SET(ls, &master); int maxfd = ls;
for (;;) {
    rd = master;
    select(maxfd + 1, &rd, NULL, NULL, NULL);
    if (FD_ISSET(ls, &rd)) { int c = accept(ls, NULL, NULL); FD_SET(c, &master); if (c > maxfd) maxfd = c; }
    for (int fd = 0; fd <= maxfd; fd++)
        if (fd != ls && FD_ISSET(fd, &rd)) {
            ssize_t n = recv(fd, buf, sizeof buf, 0);
            if (n <= 0) { close(fd); FD_CLR(fd, &master); }
            else { /* xử lý */ }
        }
}
```

## 7. Giới hạn N client

- Đủ N thì vẫn `accept`, gửi thông báo theo đề (vd. `FULL`), `close` ngay.
- Giảm `nclients` ở **mọi** đường client rời đi (`QUIT`, `recv == 0`, lỗi).
- Mỗi client có **bộ đệm dòng riêng** và trạng thái riêng (đã đăng ký/đăng nhập chưa).
- Dữ liệu dùng chung (bảng key-value, phòng chat): dùng select/poll hoặc thread + mutex, **không** dùng fork.

## 8. Tệp & HTTP

- Ghi nối tiếp: `fopen(path, "ab")`; `fflush`/`fclose` để dữ liệu nằm trong tệp ngay. `"w"` ghi đè.
- Dữ liệu mạng có thể chứa `0x00`: dùng số byte (`n`), không dùng `strlen`.
- HTTP: header kết thúc `\r\n\r\n`; `Content-Length` = số byte **thân**; kiểm tra lỗi theo thứ tự 400 → 405 → 403 → 404 → 200.

## 9. Verdict của bộ chấm

| Verdict | Hay do |
|---|---|
| WA | không ghép dòng / không đọc đủ byte; quên `htons`/`htonl`; dùng `strlen` với dữ liệu nhị phân |
| RE | server thoát sau một client; truy cập mảng sai |
| BLOCKED | `recv`/`accept` blocking trong vòng chính; `pthread_join` ngay; cha `wait` con |
| LIMIT | điều kiện từ chối sai, đếm client sai |
| CV | dùng hàm bị cấm (`fork`, `pthread`, `select`, `poll`...) |
| NL | không `listen` đúng cổng (`htons`, `argv[1]`) |
| TLE | vòng lặp không thoát (`recv == 0`), chờ dữ liệu không bao giờ đến |
