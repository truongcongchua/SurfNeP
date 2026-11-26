# Server ghi nối tiếp dữ liệu client vào tệp

Viết server chạy bằng:

```
./tcp_server <cổng> <tệp log>
```

Với **mỗi** client kết nối đến (phục vụ lần lượt từng client là đủ):

1. Nhận mọi dữ liệu client gửi đến và **ghi nối tiếp** vào cuối `<tệp log>` cho đến khi client đóng kết nối.
   Không ghi đè dữ liệu của client trước. Nếu tệp chưa tồn tại thì tạo mới; nếu đã có nội dung thì ghi tiếp vào cuối.
2. Xong một client thì dữ liệu phải **nằm trong tệp** ngay (`write` vào tệp ngay; nếu dùng `fwrite` thì `fclose`/`fflush`),
   không đợi server kết thúc.
3. Server **không gửi** gì cho client. Đóng kết nối rồi quay lại `accept`.

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu client gửi là nhị phân bất kỳ (có byte `0x00`, không có `\n` cuối), có thể tới 100 KB, có thể đến thành
  nhiều mảnh nhỏ: ghi đúng từng byte `recv` trả về (đừng dùng `strlen` hay các hàm xử lý xâu).
- Client không gửi gì thì log không được thêm byte nào (cũng không thêm `\n`).
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ `close` cả tệp log và
  client mỗi lần).

## Ví dụ

```
$ ./tcp_server 9000 log.txt
```

Client 1 gửi `abc\n` rồi đóng. Client 2 gửi `xyz\n` rồi đóng. Khi đó `log.txt` chứa `abc\nxyz\n`.

## Kiến thức nền
Vòng `recv` đến khi trả `<= 0` như `tcp-echo`, nhưng thay vì `send` lại thì ghi vào tệp. Bạn được dùng **một trong hai** nhóm hàm
làm việc với tệp (bộ chấm không phân biệt). Quy trình: **mở (chế độ ghi nối) → ghi từng khối `recv` được → đóng**.

**Cách 1: `open`/`write`/`close` (lab08, file descriptor `int`)**

```c
#include <fcntl.h>
#include <unistd.h>

int fd = open(argv[2], O_WRONLY | O_CREAT | O_APPEND, 0644);  // -1 nếu lỗi
while ((n = recv(client, buffer, sizeof(buffer), 0)) > 0)
    write(fd, buffer, n);                  // ghi đúng n byte, vào tệp ngay
close(fd);
```

`O_APPEND` ghi nối vào cuối (thiếu nó thì ghi đè từ đầu tệp), `O_CREAT` tạo tệp nếu chưa có và đòi tham số thứ ba (quyền,
ví dụ `0644`), còn `O_TRUNC` sẽ xoá dữ liệu cũ nên **đừng** dùng.

**Cách 2: `fopen`/`fwrite`/`fclose` (`FILE *`)**

```c
FILE *f = fopen(argv[2], "ab");            // "ab" = ghi nối vào cuối, nhị phân; "wb" sẽ xoá dữ liệu cũ
while ((n = recv(client, buffer, sizeof(buffer), 0)) > 0)
    fwrite(buffer, 1, n, f);               // ghi đúng n byte (không dùng fputs/strlen)
fclose(f);                                 // đẩy bộ đệm xuống tệp rồi đóng
```

`fwrite` ghi vào bộ đệm của thư viện, dữ liệu chỉ chắc chắn nằm trong tệp sau `fflush(f)` hoặc `fclose(f)`; hãy `fclose`
ngay khi xong một client.

Dù dùng cách nào: kiểm tra mở tệp không lỗi (`-1` hoặc `NULL`), ghi đúng `n` byte `recv` trả về, đóng tệp rồi
`close(client)`. Bài này là nửa "ghi log" của `tcp-greeting-log`.
