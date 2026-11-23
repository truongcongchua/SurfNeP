---
title: "Ghép kênh I/O với select"
chapter: 3
ref: "Lecture notes §3.5 (tr.84); L5-IOMultiplexing/select_server.c, select_client.c"
---

## Hiểu nhanh
Bạn là nhân viên phục vụ một mình cho nhiều bàn. Thay vì chạy qua hỏi từng bàn liên tục (cách non-blocking), bạn **đứng chờ ở quầy**, bàn nào bấm chuông thì mới tới bàn đó.

`select` chính là cái chuông: bạn đưa cho hệ điều hành **danh sách socket** cần theo dõi, rồi chương trình ngủ cho đến khi **có ít nhất một socket sẵn sàng** (có dữ liệu để đọc, hoặc có client mới). Hàm trả về cho biết socket nào sẵn sàng.

Lợi ích: một chương trình, một luồng, phục vụ nhiều client, không tốn CPU vô ích, không cần khoá (mutex) vì chỉ có một luồng.

"Socket nghe sẵn sàng" nghĩa là có client mới đang chờ → gọi `accept` sẽ không bị chặn.

## `fd_set` và 4 macro
`fd_set` là một **tập hợp các số fd**:

| Macro | Việc làm |
|---|---|
| `FD_ZERO(&set)` | làm rỗng tập |
| `FD_SET(fd, &set)` | thêm `fd` vào tập |
| `FD_CLR(fd, &set)` | bỏ `fd` khỏi tập |
| `FD_ISSET(fd, &set)` | `fd` có trong tập không? |

**Điểm quan trọng:** `select` **sửa** tập bạn đưa vào, chỉ để lại những fd sẵn sàng. Vì vậy, như `select_server.c`, giữ danh sách client trong một **mảng** và mỗi vòng **dựng lại** `fd_set` từ mảng đó.

## Mẫu server (theo `select_server.c`)
```c
#include <sys/select.h>

fd_set read_fds;
int client_list[50];
int number_of_clients = 0;

while (1) {
    FD_ZERO(&read_fds);                          // dựng lại tập mỗi vòng
    FD_SET(listener, &read_fds);
    int max_fd = listener;
    for (int i = 0; i < number_of_clients; i++) {
        FD_SET(client_list[i], &read_fds);
        if (client_list[i] > max_fd) max_fd = client_list[i];
    }
    if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) continue;

    // 1. Socket nghe sẵn sàng → có client mới
    if (FD_ISSET(listener, &read_fds)) {
        int client_socket = accept(listener, NULL, NULL);
        client_list[number_of_clients++] = client_socket;
    }

    // 2. Client nào có dữ liệu?
    for (int i = 0; i < number_of_clients; i++) {
        int client_socket = client_list[i];
        if (!FD_ISSET(client_socket, &read_fds)) continue;
        char buffer[1024];
        int n = recv(client_socket, buffer, sizeof(buffer), 0);
        if (n <= 0) {                            // client đóng hoặc lỗi
            close(client_socket);
            client_list[i] = client_list[number_of_clients - 1];   // xoá khỏi mảng
            number_of_clients--;
            i--;
        } else {
            /* xử lý n byte trong buffer */
        }
    }
}
```
- Tham số đầu của `select` là **`max_fd + 1`** (fd lớn nhất cộng 1), **không phải** số lượng fd.
- Ba tham số tiếp theo: tập theo dõi **đọc**, **ghi**, **ngoại lệ**. Thường chỉ cần đọc, hai cái kia để `NULL`.
- Tham số cuối là thời gian chờ tối đa (`struct timeval`); `NULL` = chờ mãi.
- `select` chỉ theo dõi được fd nhỏ hơn `FD_SETSIZE` (thường 1024).
- Code mẫu gốc `close` client nhưng **không xoá** khỏi `client_list`; vòng sau nó lại `FD_SET` một fd đã đóng. Hãy xoá như trên.

## Mẫu client (theo `select_client.c`)
Client vừa đọc bàn phím vừa nhận tin: theo dõi cùng lúc `STDIN_FILENO` và socket.
```c
while (1) {
    FD_ZERO(&read_fds);
    FD_SET(client_socket, &read_fds);
    FD_SET(STDIN_FILENO, &read_fds);
    int max_fd = (client_socket > STDIN_FILENO) ? client_socket : STDIN_FILENO;
    struct timeval timeout;
    timeout.tv_sec = 5;                          // gán lại MỖI vòng
    timeout.tv_usec = 0;
    int activity = select(max_fd + 1, &read_fds, NULL, NULL, &timeout);
    if (activity < 0) break;
    if (activity == 0) { /* hết 5 giây mà không có gì */ }
    if (FD_ISSET(client_socket, &read_fds)) { /* recv rồi in ra */ }
    if (FD_ISSET(STDIN_FILENO, &read_fds)) { /* đọc stdin rồi send */ }
}
```
Trên Linux, `select` **trừ dần** thời gian đã chờ vào `timeout`. Code mẫu gán `timeout` một lần ngoài vòng lặp nên chỉ lần đầu chờ đủ 5 giây; hãy gán lại trước mỗi lần gọi.

## Hạn chế cần biết
Chỉ có một luồng, nên nếu đang xử lý một client mà làm việc **lâu** (`sleep`, `system()`, đọc tệp lớn), mọi client khác phải chờ.

## Lỗi hay gặp
- **Sau vòng đầu không nhận được gì nữa.** Chỉ `FD_SET` một lần ngoài vòng lặp nên tập bị `select` sửa mất. Sửa: `FD_ZERO` + `FD_SET` lại mỗi vòng.
- **Client mới không bao giờ được phục vụ.** Truyền `max_fd` thay vì `max_fd + 1`, hoặc quên cập nhật `max_fd`.
- **`select` báo lỗi `Bad file descriptor`.** Đã `close(fd)` nhưng vẫn để fd trong mảng client.
- **Dòng lệnh bị trộn giữa các client.** Dùng chung một bộ đệm. Mỗi client cần **bộ đệm riêng** để ghép dòng (xem thẻ *Quản lý nhiều client*).
