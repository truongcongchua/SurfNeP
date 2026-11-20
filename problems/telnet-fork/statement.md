# Server Telnet đa tiến trình

Viết `./telnet_server <cổng>` với **cùng giao thức** như bài *telnet-select* (đăng nhập bằng
`accounts.txt`, `OUTPUT <n>` + kết quả, `exit` → `BYE`), nhưng mỗi client được phục vụ bởi
**một tiến trình con** (`fork`). **Không được dùng:** `select`, `poll`, `epoll`, `pthread`.

## Điều bài này kiểm tra thêm
Một client chạy lệnh **chậm** (`sleep 1.5; echo xong`) thì client khác vẫn được trả lời ngay.
Phiên bản `select()` không làm được điều này vì `system()` chặn cả server.

## Ràng buộc và bộ chấm kiểm tra
- Đăng nhập phải **khớp nguyên dòng** với một dòng của `accounts.txt` (phân biệt hoa thường; thừa/thiếu dấu cách,
  tab, tiền tố như `admin adm` đều là `LOGIN FAIL`). Bỏ `\r` cuối dòng. Mọi dòng trước khi đăng nhập thành công,
  kể cả `exit`, đều là một lần đăng nhập.
- Một dòng lệnh dài tới 1000 byte và có thể gồm **nhiều lệnh** (`echo a; echo b`, `a | b`): gom kết quả của cả
  dòng (gợi ý: `system("{ <lệnh>\n} > tệp 2>&1")`). Dòng lệnh rỗng → `OUTPUT 0`. Chỉ đúng dòng `exit` mới thoát.
- `n` là **số byte thật** của kết quả: kết quả có thể chứa byte `0x00` (không dùng `strlen`), có thể rỗng, hoặc
  lớn tới vài MB.
- Lệnh có thể đến từng byte một, hoặc dòng đăng nhập + hàng chục lệnh dính nhau trong một lần gửi.
- Client có thể đóng đột ngột (RST) khi server đang gửi kết quả. Chương trình chạy với giới hạn 256 file
  descriptor: bộ chấm thử 300 lần đăng nhập sai và 300 phiên liên tiếp (nhớ `fclose`/`close`).
- Bộ chấm đếm zombie sau khi 30 phiên kết thúc **cùng lúc** (nhiều `SIGCHLD` bị gộp làm một).

## Hai cái bẫy
1. **Zombie:** cha phải `waitpid` các con đã kết thúc (handler `SIGCHLD`, xem bài *fork-echo*).
2. **`system()` trong tiến trình con:** nếu tiến trình con thừa hưởng handler `SIGCHLD` gọi
   `waitpid(-1, ...)`, handler sẽ thu dọn mất tiến trình mà `system()` đang chờ, khiến `system()`
   báo lỗi. Trong tiến trình con hãy đặt lại `signal(SIGCHLD, SIG_DFL)`.

## Kiến thức nền
Lecture notes §3.3; code mẫu `forking_server.c`, `telnet_server.c`.
