---
title: "Socket non-blocking"
chapter: 3
ref: "Lecture notes §3.1 (tr.48); L1-NonBlocking/non_blocking_server.c"
---

## Hiểu nhanh
Mặc định `accept`, `recv` là **blocking** (chặn): gọi `recv` mà chưa có dữ liệu thì chương trình **đứng im chờ**, giống bạn đứng trước cửa chờ bưu tá. Trong lúc đó không làm được gì khác, kể cả phục vụ client khác.

**Non-blocking** (không chặn): gọi `recv` mà chưa có dữ liệu thì hàm **trả về ngay** `-1`, nghĩa là "chưa có gì", giống liếc qua hộp thư rồi đi làm việc khác. Nhờ vậy một vòng lặp có thể lần lượt hỏi nhiều client.

## Bật chế độ non-blocking
Như code mẫu `non_blocking_server.c`:
```c
#include <sys/ioctl.h>

int io_mode = 1;                     // 1 = bật non-blocking, 0 = tắt
ioctl(listener, FIONBIO, &io_mode);  // socket nghe: accept không chặn nữa
```
Mỗi client vừa `accept` cũng phải `ioctl(client, FIONBIO, &io_mode)`, nếu không `recv` trên client đó vẫn chặn cả server.

## Đọc kết quả `recv` khi non-blocking
Có thêm một trường hợp: trả `-1` nhưng **không phải lỗi**.

| Kết quả | Nghĩa là | Nên làm |
|---|---|---|
| `> 0` | có dữ liệu | xử lý |
| `0` | client đã đóng | `close(fd)`, xoá khỏi mảng |
| `-1` | **chưa có dữ liệu** | bỏ qua, sang client khác |

## Mẫu: một vòng lặp phục vụ nhiều client
```c
int io_mode = 1;
ioctl(listener, FIONBIO, &io_mode);          // socket nghe cũng phải non-blocking
int client_sockets[MAX]; int num_clients = 0;

while (0 == 0) {
    // 1. Có khách mới không? (không có thì accept trả -1 ngay, không chờ)
    int client = accept(listener, NULL, NULL);
    if (client != -1) {
        ioctl(client, FIONBIO, &io_mode);
        client_sockets[num_clients++] = client;
    }

    // 2. Hỏi lần lượt từng client
    for (int i = 0; i < num_clients; i++) {
        char buffer[1024];
        int n = recv(client_sockets[i], buffer, sizeof(buffer), 0);
        if (n > 0) {
            send(client_sockets[i], buffer, n, 0);
        } else if (n == 0) {
            close(client_sockets[i]);                           // đóng rồi xoá khỏi mảng
            client_sockets[i] = client_sockets[num_clients - 1]; // phần tử cuối vào chỗ trống
            num_clients--;
            i--;                                                // xét lại vị trí i
        }
        // n == -1: chưa có gì, bỏ qua
    }
}
```
Code mẫu gốc chỉ `close` mà không xoá client khỏi mảng, nên mảng cứ dài mãi; hãy xoá như trên.

## Nhược điểm
- Vòng lặp trên phải **hỏi tất cả client liên tục**, kể cả khi không ai gửi gì: tốn CPU (gọi là **bận chờ**, busy-wait).
- `send` trên socket non-blocking **không chờ**: nếu bộ đệm gửi đầy (client không chịu đọc), phần không gửi được bị bỏ dở.

Cách tốt hơn là để hệ điều hành **báo** client nào có dữ liệu: đó là `select` (xem thẻ *Ghép kênh I/O với select*).

## Lỗi hay gặp
- **Client bị đóng vô cớ.** Coi `recv == -1` là lỗi và đóng client. Trên socket non-blocking, `-1` thường chỉ nghĩa là "chưa có dữ liệu".
- **Cả server vẫn bị treo.** Quên đặt non-blocking cho **socket nghe** (nên `accept` vẫn đứng chờ) hoặc cho **client** (nên `recv` đứng chờ).
- **Chạy lâu thì hết chỗ trong mảng.** Client đóng mà không xoá khỏi `client_sockets`.
