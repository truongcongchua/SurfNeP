---
title: "Server đa tiến trình (fork)"
chapter: 3
ref: "Lecture notes §3.3 (tr.55); L3-MultiProcessing/forking_server.c"
---

## Tóm tắt
Mỗi client được một **tiến trình con** phục vụ. Tiến trình cha chỉ `accept`. Các tiến trình có **bộ nhớ riêng** nên không chia sẻ biến (nếu cần dùng chung dữ liệu thì phải dùng IPC; đó là lý do bài key-value dùng thread/select).

```c
signal(SIGCHLD, sigchld_handler);            // chống zombie

for (;;) {
    int c = accept(s, NULL, NULL);
    pid_t pid = fork();
    if (pid == 0) {                          // ----- tiến trình con
        close(s);                            // con không cần socket nghe
        serve(c);
        close(c);
        exit(0);
    }
    close(c);                                // ----- cha không cần socket của client
}

void sigchld_handler(int sig) {
    while (waitpid(-1, NULL, WNOHANG) > 0);  // thu dọn mọi con đã kết thúc
}
```

## Quy tắc đóng descriptor
Sau `fork`, **cả hai** tiến trình đều giữ cả `s` lẫn `c`. Mỗi bên phải đóng cái mình không dùng:
- Con: `close(s)`.
- Cha: `close(c)`. Nếu không, socket `c` không bao giờ thực sự đóng (bộ đếm tham chiếu vẫn > 0) → client không nhận được EOF và rò rỉ fd ở cha.

## Zombie
Con kết thúc mà cha không `wait` → thành **zombie** (vẫn chiếm một dòng trong bảng tiến trình). Xử lý: handler `SIGCHLD` gọi `waitpid(-1, NULL, WNOHANG)` trong vòng `while` (vì nhiều tín hiệu có thể gộp thành một).

## Bẫy thường gặp
- Quên `close(c)` ở cha.
- Handler dùng `wait()` một lần thay vì vòng `while waitpid(..., WNOHANG)`.
- `accept` bị ngắt bởi tín hiệu trả `-1` với `errno == EINTR` → phải thử lại, không thoát.
- Con kế thừa handler `SIGCHLD` rồi gọi `system()`: handler thu dọn mất tiến trình mà `system()` đang chờ. Trong con đặt lại `signal(SIGCHLD, SIG_DFL)`.
- Con quên `exit(0)` → rơi xuống vòng `accept` của cha, nhân đôi server.
- Giới hạn số client: đếm bằng biến ở cha không đủ vì con kết thúc không báo trực tiếp (phải cập nhật trong handler).
