# telnet_server đa tiến trình (Bài tập 3.4)

Viết `./telnet_server <cổng>` với **cùng giao thức** như bài *telnet-select* (đăng nhập bằng
`accounts.txt`, `OUTPUT <n>` + kết quả, `exit` → `BYE`), nhưng mỗi client được phục vụ bởi
**một tiến trình con** (`fork`). **Không được dùng:** `select`, `poll`, `epoll`, `pthread`.

## Điều bài này kiểm tra thêm
Một client chạy lệnh **chậm** (`sleep 1.5; echo xong`) thì client khác vẫn được trả lời ngay.
Phiên bản `select()` không làm được điều này vì `system()` chặn cả server.

## Hai cái bẫy
1. **Zombie:** cha phải `waitpid` các con đã kết thúc (handler `SIGCHLD`, xem bài *fork-echo*).
2. **`system()` trong tiến trình con:** nếu tiến trình con thừa hưởng handler `SIGCHLD` gọi
   `waitpid(-1, ...)`, handler sẽ thu dọn mất tiến trình mà `system()` đang chờ, khiến `system()`
   báo lỗi. Trong tiến trình con hãy đặt lại `signal(SIGCHLD, SIG_DFL)`.

## Kiến thức nền
Lecture notes §3.3; code mẫu `forking_server.c`, `telnet_server.c`.
