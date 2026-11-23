---
title: "Vòng đời socket TCP (server & client)"
chapter: 2
ref: "Lecture notes §2.3 (tr.22)"
---

## Hiểu nhanh
Hãy hình dung server TCP là **tổng đài của một cửa hàng**:

| Bước | Hàm | Đời thường |
|---|---|---|
| 1 | `socket` | mua một chiếc điện thoại |
| 2 | `bind` | đăng ký số máy (địa chỉ IP + cổng) |
| 3 | `listen` | bật chuông, sẵn sàng nhận cuộc gọi |
| 4 | `accept` | nhấc máy, chuyển khách sang **một máy riêng** để nói chuyện |
| 5 | `recv` / `send` | nghe / nói |
| 6 | `close` | cúp máy |

Client đơn giản hơn: `socket` (mua điện thoại) → `connect` (bấm số gọi) → `send`/`recv` → `close`.

## Hai loại socket ở server, đừng nhầm
- **Socket nghe** (`listen_fd`): chỉ dùng để `accept` khách mới. **Không** `recv`/`send` trên nó.
- **Socket kết nối** (`fd` do `accept` trả về): mỗi client có **một cái riêng**. Mọi việc đọc/ghi với client đó đều dùng `fd` này.

## Code mẫu: server
```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    int port = atoi(argv[1]);

    // 1. Tạo socket TCP (SOCK_STREAM = TCP)
    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) { perror("socket"); return 1; }

    // Cho phép chạy lại server ngay, không bị "Address already in use"
    int yes = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);

    // 2. Gắn địa chỉ: mọi IP của máy (INADDR_ANY), cổng = port
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);                 // htons: xem thẻ "Thứ tự byte"
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof addr) < 0) { perror("bind"); return 1; }

    // 3. Bắt đầu nghe; 16 = số client được xếp hàng chờ accept
    listen(listen_fd, 16);

    for (;;) {
        // 4. Chờ một client. accept trả về socket MỚI dành riêng cho client này
        int fd = accept(listen_fd, NULL, NULL);
        if (fd < 0) continue;

        // 5. Nói chuyện: nhận gì gửi lại nấy (echo)
        char buf[1024];
        ssize_t n;
        while ((n = recv(fd, buf, sizeof buf, 0)) > 0)
            send(fd, buf, n, 0);                 // gửi lại đúng n byte vừa nhận

        // 6. Client đã thoát (recv trả 0) → đóng socket của client đó
        close(fd);
    }
}
```

## Code mẫu: client
```c
int fd = socket(AF_INET, SOCK_STREAM, 0);

struct sockaddr_in srv = {0};
srv.sin_family = AF_INET;
srv.sin_port = htons(port);
srv.sin_addr.s_addr = inet_addr("127.0.0.1");    // đổi xâu IP sang dạng máy hiểu

if (connect(fd, (struct sockaddr *)&srv, sizeof srv) < 0) { perror("connect"); return 1; }

char line[1024];
while (fgets(line, sizeof line, stdin))           // đọc từng dòng bàn phím
    send(fd, line, strlen(line), 0);              // xâu do mình gõ nên dùng strlen được
close(fd);
```

## Đọc kết quả của `recv`
`recv(fd, buf, size, 0)` trả về một số, và bạn **luôn** phải xét cả ba trường hợp:

| Kết quả | Nghĩa là | Nên làm |
|---|---|---|
| `> 0` | nhận được chừng ấy byte (có thể **ít hơn** `size`) | xử lý đúng số byte đó |
| `0` | phía bên kia đã **đóng** kết nối | thoát vòng lặp, `close(fd)` |
| `-1` | có lỗi | in `perror`, đóng kết nối |

`send` trên socket **blocking** (mặc định) tự chờ tới khi đã đưa hết dữ liệu vào bộ đệm gửi, nên gọi một lần là đủ, như `tcp_server.c`: `send(client, buffer, bytes_received, 0)`. Chỉ cần kiểm tra `== -1` (lỗi). Ngược lại, `recv` thì **có thể** trả ít hơn số byte bạn xin: dữ liệu lớn đến qua nhiều lần `recv`.

## Lỗi hay gặp
- **Chạy lại server báo `bind: Address already in use`.** Cổng cũ vẫn bị hệ điều hành giữ vài chục giây. Sửa: thêm `setsockopt(... SO_REUSEADDR ...)` **trước** `bind`.
- **Server không nhận được gì / báo lỗi khi `recv`.** Bạn đang `recv` trên `listen_fd`. Sửa: dùng `fd` mà `accept` trả về.
- **Client thoát rồi mà server chạy vòng lặp vô hạn, CPU 100%.** Không kiểm tra `recv` trả `0`. Sửa: dừng vòng lặp khi `n <= 0`.
- **Chạy được vài trăm client thì server hỏng.** Quên `close(fd)` sau mỗi client, hết số descriptor.
- **Dữ liệu gửi lại bị cụt.** Dùng `strlen(buf)` thay vì `n`. Dữ liệu nhận về **không có** `'\0'` ở cuối và có thể chứa `'\0'` ở giữa. Luôn dùng `n`.
