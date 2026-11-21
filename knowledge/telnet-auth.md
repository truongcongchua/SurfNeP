---
title: "Telnet server: đăng nhập & chạy lệnh"
chapter: 3
ref: "Lecture notes §3.3, §3.6 Bài tập 3.4; telnet_server.c"
---

## Bài toán
Server cho phép điều khiển máy từ xa qua mạng:
1. Client gửi **tên đăng nhập** và **mật khẩu**.
2. Server so với tệp tài khoản. Đúng thì cho vào, sai thì báo lỗi.
3. Sau khi đăng nhập, client gửi **lệnh** (vd. `ls -l`), server chạy lệnh và gửi lại kết quả.

## Mỗi client đang ở bước nào? (trạng thái)
Server phải nhớ từng client đang ở bước nào để hiểu dòng tiếp theo là gì:

```
CHO_USER ──(gửi tên)──▶ CHO_PASS ──(mật khẩu đúng)──▶ DA_DANG_NHAP ──(gửi lệnh)──▶ chạy lệnh
                            │
                            └──(sai)──▶ báo lỗi, quay về CHO_USER
```
```c
enum { CHO_USER, CHO_PASS, DA_DANG_NHAP };
// select/poll: lưu state, user trong struct riêng của từng client
// fork: dùng biến cục bộ trong tiến trình con là đủ
```

## Kiểm tra tài khoản
Tệp `accounts.txt` mỗi dòng có dạng `ten matkhau`:
```c
int check_login(const char *user, const char *pass) {
    FILE *f = fopen("accounts.txt", "r");
    if (!f) return 0;
    char u[64], p[64];
    int ok = 0;
    while (fscanf(f, "%63s %63s", u, p) == 2)          // đọc từng cặp tên-mật khẩu
        if (strcmp(u, user) == 0 && strcmp(p, pass) == 0) { ok = 1; break; }
    fclose(f);
    return ok;
}
```
`%63s` giới hạn đọc tối đa 63 ký tự để không tràn mảng 64.

## Chạy lệnh và lấy kết quả
Cách 1, `popen`: chạy lệnh và đọc kết quả như đọc tệp.
```c
FILE *p = popen(cmd, "r");                    // chạy cmd, "r" = đọc những gì nó in ra
if (p) {
    char out[4096];
    size_t n;
    while ((n = fread(out, 1, sizeof out, p)) > 0)
        send_all(fd, out, n);
    pclose(p);
}
```
Cách 2, `system` + tệp tạm: `system("ls -l > out.txt")` rồi đọc `out.txt` gửi cho client.

## Client làm sao biết kết quả đã hết?
TCP không có ranh giới (xem thẻ *TCP là luồng byte*), nên giao thức cần đánh dấu chỗ kết thúc, ví dụ gửi trước `OUTPUT <số byte>\n` rồi mới đến kết quả, hoặc kết thúc bằng một dòng đặc biệt. Làm đúng định dạng đề yêu cầu.

## Lỗi hay gặp
- **Mật khẩu đúng mà vẫn báo sai.** Telnet gửi `"pass\r\n"`, bạn chỉ bỏ `\n` nên còn `\r`. Sửa: bỏ cả `\r` và `\n` cuối dòng trước khi so sánh hoặc chạy lệnh.
- **Chưa đăng nhập vẫn chạy được lệnh.** Quên kiểm tra trạng thái `DA_DANG_NHAP` trước khi chạy.
- **Một lệnh chậm làm treo tất cả client.** `system`/`popen` **chặn** cho đến khi lệnh chạy xong. Với `select` thì cả server đứng; với `fork` chỉ con đó đứng. Đây là điểm khác giữa hai cách cài.
- **`system()` trong tiến trình con báo lỗi lạ.** Xem lỗi về `SIGCHLD` ở thẻ *fork*.
- Chạy lệnh do người khác gửi là **rất nguy hiểm** ngoài đời thật (kẻ xấu chạy được mọi thứ trên máy bạn). Chỉ chấp nhận trong bài thực hành.
