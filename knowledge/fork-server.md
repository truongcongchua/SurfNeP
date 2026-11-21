---
title: "Server đa tiến trình (fork)"
chapter: 3
ref: "Lecture notes §3.3 (tr.55); L3-MultiProcessing/forking_server.c"
---

## Hiểu nhanh
`fork()` **nhân bản** chương trình đang chạy thành hai: tiến trình **cha** (bản gốc) và tiến trình **con** (bản sao). Hai bên chạy tiếp từ cùng một dòng code, chỉ khác giá trị trả về của `fork()`:

| `fork()` trả về | Bạn đang ở |
|---|---|
| `0` | tiến trình **con** |
| số dương (PID của con) | tiến trình **cha** |
| `-1` | lỗi, không tạo được con |

Server dùng `fork` giống **lễ tân và nhân viên**: cha (lễ tân) chỉ đứng `accept` khách; mỗi khách mới, cha "sinh" một con (nhân viên) đi phục vụ riêng khách đó, rồi cha quay lại đón khách tiếp.

Con là **bản sao**: có bộ nhớ riêng. Con sửa biến thì cha và các con khác **không thấy**.

## Code mẫu
```c
#include <signal.h>
#include <sys/wait.h>

void on_child_exit(int sig) {
    while (waitpid(-1, NULL, WNOHANG) > 0);   // dọn MỌI con đã kết thúc
}

int main() {
    /* socket, bind, listen như thẻ "Vòng đời socket TCP" */
    signal(SIGCHLD, on_child_exit);           // con kết thúc → gọi hàm dọn dẹp

    for (;;) {
        int c = accept(listen_fd, NULL, NULL);
        if (c < 0) continue;                  // bị tín hiệu ngắt (EINTR) → thử lại

        pid_t pid = fork();
        if (pid == 0) {                       // ===== CON =====
            close(listen_fd);                 // con không cần đón khách
            serve(c);                         // phục vụ client
            close(c);
            exit(0);                          // BẮT BUỘC: kết thúc con tại đây
        }
        close(c);                             // ===== CHA ===== cha không nói chuyện với client
    }
}
```

## Vì sao mỗi bên phải `close` một socket?
Sau `fork`, **cả cha lẫn con** đều đang cầm cả `listen_fd` và `c`. Socket chỉ thật sự đóng khi **mọi** tiến trình cầm nó đều `close`.
- Con `close(listen_fd)`: con không cần đón khách.
- Cha `close(c)`: nếu cha giữ `c`, khi con đóng xong thì kết nối vẫn chưa đóng hẳn → client không biết server đã xong; đồng thời cha tích tụ hàng trăm socket thừa.

## Tiến trình "zombie" là gì?
Con kết thúc nhưng cha chưa "nhận tin" (`wait`) thì con thành **zombie**: không chạy nữa nhưng vẫn chiếm một chỗ trong bảng tiến trình. Nhiều zombie thì hết chỗ tạo con mới.

Cách xử lý: khi con kết thúc, hệ điều hành gửi tín hiệu `SIGCHLD` cho cha. Đăng ký hàm `on_child_exit` ở trên để dọn. Dùng **vòng `while`** vì nhiều con kết thúc cùng lúc có thể chỉ sinh **một** tín hiệu. `WNOHANG` để `waitpid` không đứng chờ khi không còn con nào cần dọn.

## Lỗi hay gặp
- **Client không nhận được tín hiệu kết thúc / cha hết descriptor.** Quên `close(c)` ở cha.
- **Server bị nhân đôi, chạy loạn.** Con quên `exit(0)`, chạy tiếp xuống vòng `accept` như một server thứ hai.
- **Danh sách tiến trình đầy `<defunct>`.** Không xử lý `SIGCHLD`, hoặc dùng `wait()` một lần thay vì vòng `while waitpid(..., WNOHANG)`.
- **Server tự thoát khi có con kết thúc.** `accept` bị tín hiệu ngắt, trả `-1` với `errno == EINTR`, và code thoát luôn. Phải `continue`.
- **`system()` trong con trả kết quả sai.** Con thừa hưởng hàm dọn `SIGCHLD` của cha, hàm này dọn luôn tiến trình mà `system()` đang chờ. Trong con, đặt lại `signal(SIGCHLD, SIG_DFL);` trước khi gọi `system()`.
- **Đếm số client sai.** Biến đếm ở cha không tự giảm khi con kết thúc (con có bản sao riêng). Giảm trong hàm xử lý `SIGCHLD`.
