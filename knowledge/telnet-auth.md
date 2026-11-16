---
title: "Telnet server: đăng nhập & chạy lệnh"
chapter: 3
ref: "Lecture notes §3.3, §3.6 Bài tập 3.4; telnet_server.c"
---

## Bài toán
Client gửi tên đăng nhập/mật khẩu, được xác thực bằng tệp tài khoản, sau đó gửi lệnh shell; server chạy lệnh và trả kết quả.

## Xác thực với tệp tài khoản
```c
// accounts.txt: mỗi dòng "user pass"
FILE *f = fopen("accounts.txt", "r");
char u[64], p[64];
while (fscanf(f, "%63s %63s", u, p) == 2)
    if (!strcmp(u, user) && !strcmp(p, pass)) { ok = 1; break; }
fclose(f);
```
Trạng thái mỗi client: `CHO_USER → CHO_PASS → DA_DANG_NHAP`. Lưu trong struct của từng client (với select) hoặc biến cục bộ (với fork).

## Chạy lệnh và lấy kết quả
```c
FILE *p = popen(cmd, "r");              // chạy cmd, đọc stdout của nó
char out[4096]; size_t n = fread(out, 1, sizeof out, p);
int status = pclose(p);
```
hoặc `system("cmd > out.txt")` rồi đọc tệp `out.txt`.

## Thiết kế phản hồi
Vì TCP là luồng byte, client không biết kết quả dài bao nhiêu → giao thức nên có **độ dài** (vd. `OUTPUT <n>\n` rồi `n` byte kết quả), xem thẻ *TCP là luồng byte*.

## Bẫy thường gặp
- `system()`/`popen()` **chặn** tiến trình: với `select` một lệnh chậm làm treo mọi client; với `fork` thì chỉ treo con tương ứng (đây là điểm khác nhau giữa hai bài).
- Dòng lệnh còn `\r\n` ở cuối (telnet gửi CRLF) → cắt trước khi so sánh/chạy.
- Đăng nhập thất bại vẫn cho gửi lệnh (quên kiểm tra trạng thái).
- So sánh mật khẩu có ký tự xuống dòng thừa.
- Chạy lệnh do client gửi là **rất nguy hiểm** ngoài môi trường bài tập (command injection); chỉ chấp nhận trong bài thực hành.
- `SIGCHLD` handler thu dọn mất tiến trình của `system()` (xem thẻ *fork*).
