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
| `recv` | `> 0` số byte (có thể ít hơn yêu cầu) · `0` đối phương đóng · `-1` lỗi (socket non-blocking: `-1` = chưa có dữ liệu) |
| `recvfrom` (UDP) | `>= 0` độ dài datagram (`0` = datagram **rỗng**, không phải đóng) · `-1` lỗi |
| `send` | số byte đã gửi · `-1` lỗi (socket blocking: chờ tới khi gửi hết) |
| `inet_addr` | `s_addr` (thứ tự mạng) · `INADDR_NONE` xâu sai (trùng với `255.255.255.255`!) |
| `getaddrinfo` | `0` thành công (kết quả là danh sách `ai_next`, nhớ `freeaddrinfo`) · khác `0` là lỗi |
| `select` | số fd sẵn sàng · `0` hết thời gian chờ · `-1` lỗi |
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
| Non-blocking | `ioctl(fd, FIONBIO, &io_mode)`, thử liên tục | dễ | `recv == -1` là chưa có dữ liệu; bận chờ 100% CPU |
| `fork` | mỗi client một tiến trình | **không** (bộ nhớ riêng) | `SIGCHLD` + `waitpid(WNOHANG)` chống zombie; con đóng socket nghe, cha đóng socket client |
| `pthread` | mỗi client một luồng | có (cần **mutex**) | `malloc` tham số cho từng luồng; `pthread_detach` (không `join` ngay); `-pthread` |
| `select` | một luồng, tập `fd_set` | dễ, không cần khoá | dựng lại `fd_set` mỗi vòng; `max_fd + 1`; xoá fd khỏi mảng khi đóng; lệnh chậm chặn tất cả |

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

**Nhận đủ n byte** (`recv` có thể trả ít hơn số byte xin; `send` trên socket blocking thì tự chờ gửi hết)
```c
int got = 0;
while (got < n) {
    int r = recv(fd, buf + got, n - got, 0);
    if (r <= 0) break;          // đối phương đóng hoặc lỗi
    got += r;
}
```

**Chống zombie (fork)**
```c
void reap(int sig) { while (waitpid(-1, NULL, WNOHANG) > 0); }
signal(SIGCHLD, reap);
```

**Vòng lặp select (như `select_server.c`)**
```c
int cl[50], n = 0;
for (;;) {
    fd_set rd; FD_ZERO(&rd); FD_SET(ls, &rd); int max_fd = ls;
    for (int i = 0; i < n; i++) { FD_SET(cl[i], &rd); if (cl[i] > max_fd) max_fd = cl[i]; }
    select(max_fd + 1, &rd, NULL, NULL, NULL);
    if (FD_ISSET(ls, &rd)) cl[n++] = accept(ls, NULL, NULL);
    for (int i = 0; i < n; i++)
        if (FD_ISSET(cl[i], &rd)) {
            int k = recv(cl[i], buf, sizeof(buf), 0);
            if (k <= 0) { close(cl[i]); cl[i--] = cl[--n]; }
            else { /* xử lý */ }
        }
}
```

## 7. Giới hạn N client

- Đủ N thì vẫn `accept`, gửi thông báo theo đề (vd. `FULL`), `close` ngay.
- Giảm `nclients` ở **mọi** đường client rời đi (`QUIT`, `recv == 0`, lỗi).
- Mỗi client có **bộ đệm dòng riêng** và trạng thái riêng (đã đăng ký/đăng nhập chưa).
- Dữ liệu dùng chung (bảng key-value, phòng chat): dùng select hoặc thread + mutex, **không** dùng fork.

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
| CV | dùng hàm bị cấm (`fork`, `pthread`, `select`...) |
| NL | không `listen` đúng cổng (`htons`, `argv[1]`) |
| TLE | vòng lặp không thoát (`recv == 0`), chờ dữ liệu không bao giờ đến |
