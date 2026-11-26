# Server gửi tệp cho từng client

Viết server chạy bằng:

```
./tcp_server <cổng> <tệp>
```

Với **mỗi** client kết nối đến (phục vụ lần lượt từng client là đủ):

1. Đọc **toàn bộ** nội dung `<tệp>` và gửi cho client, giữ nguyên từng byte.
2. Gửi xong thì đóng kết nối với client đó (`close`) rồi quay lại `accept`. Server không đợi dữ liệu từ client.

Đọc lại tệp **mỗi lần** có client mới (tệp có thể đã thay đổi giữa hai client). Nếu không mở được tệp thì chỉ cần đóng kết nối
client, server vẫn phải sống.

## Ràng buộc và bộ chấm kiểm tra
- Tệp có thể rỗng, lớn tới 100 KB, hoặc chứa dữ liệu nhị phân (byte `0x00`, không có `\n` cuối): gửi **đúng từng byte**,
  không thừa không thiếu (đừng dùng `strlen` hay các hàm xử lý xâu).
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ `close` cả tệp và
  client mỗi lần).

## Ví dụ

```
$ cat data.txt
Xin chao!
$ ./tcp_server 9000 data.txt
```

Mỗi client kết nối đến nhận `Xin chao!\n` rồi bị đóng kết nối.

## Kiến thức nền
Bạn được dùng **một trong hai** nhóm hàm làm việc với tệp (bộ chấm không phân biệt). Quy trình giống nhau: **mở → đọc theo khối → gửi → đóng**.

**Cách 1: `open`/`read`/`close` (lab08, làm việc với file descriptor `int`)**

```c
#include <fcntl.h>
#include <unistd.h>

int fd = open(argv[2], O_RDONLY);          // -1 nếu không mở được
if (fd != -1) {
    int n;
    while ((n = read(fd, buffer, sizeof(buffer))) > 0)   // n = số byte đọc được, 0 = hết tệp
        send(client, buffer, n, 0);
    close(fd);
}
```

**Cách 2: `fopen`/`fread`/`fclose` (như `html.c`, làm việc với `FILE *`)**

```c
FILE *f = fopen(argv[2], "rb");            // NULL nếu không mở được; "rb" = đọc nhị phân
if (f != NULL) {
    size_t n;
    while ((n = fread(buffer, 1, sizeof(buffer), f)) > 0) // size = 1 nên n là số byte
        send(client, buffer, n, 0);
    fclose(f);
}
```

Dù dùng cách nào: gửi đúng `n` byte vừa đọc (không phải `sizeof(buffer)`, không dùng `strlen`), và luôn đóng tệp
(`close(fd)` hoặc `fclose(f)`) rồi `close(client)`.
Bài này là nửa "gửi câu chào từ tệp" của `tcp-greeting-log`.
