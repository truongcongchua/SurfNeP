# Server chào hỏi và ghi log

Viết server chạy bằng:

```
./tcp_server <cổng> <tệp chứa câu chào> <tệp lưu nội dung client gửi đến>
```

Với **mỗi** client kết nối đến (phục vụ lần lượt từng client là đủ):

1. Đọc **toàn bộ** nội dung tệp câu chào (đọc lại mỗi lần có client mới, vì tệp có thể đã thay
   đổi) và gửi cho client, giữ nguyên từng byte.
2. Nhận mọi dữ liệu client gửi đến và **ghi nối tiếp** vào tệp lưu cho đến khi client đóng kết nối.
   Không ghi đè dữ liệu của client trước. Nếu tệp chưa tồn tại thì tạo mới.
3. Ghi xong phần dữ liệu của một client thì dữ liệu phải **nằm trong tệp** ngay (`write` vào tệp ngay; nếu dùng
   `fwrite` thì `fclose`/`fflush`), không đợi server kết thúc.

## Ràng buộc và bộ chấm kiểm tra
- Câu chào có thể rỗng, lớn tới 300 KB, hoặc chứa dữ liệu nhị phân (byte `0x00`, không có `\n` cuối): gửi
  **đúng từng byte** (đừng dùng `strlen` hay các hàm xử lý xâu). Tệp có thể bị thay đổi giữa hai client.
- Dữ liệu client gửi là nhị phân bất kỳ; client không gửi gì thì log không được thêm byte nào.
- Client có thể gửi dữ liệu trước khi đọc câu chào, gửi từng mảnh nhỏ, hoặc mất kết nối đột ngột (RST) sau khi
  đã nhận câu chào.
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ `close` cả tệp câu
  chào lẫn tệp log mỗi lần).

## Ví dụ

```
$ cat greeting.txt
Xin chao! Day la server IT4062.
$ ./tcp_server 9000 greeting.txt log.txt
```

Client 1 kết nối, nhận câu chào, gửi `abc\n` rồi đóng. Client 2 gửi `xyz\n` rồi đóng.
Khi đó `log.txt` chứa `abc\nxyz\n`.

## Bài khởi động
Bài này ghép hai nửa; làm trước nếu thấy khó:
- `tcp-send-file`: nửa 1, đọc toàn bộ tệp và gửi cho client (`read` → `send`).
- `tcp-append-log`: nửa 2, nhận dữ liệu và ghi nối tiếp vào tệp log (`recv` → `write`, mở bằng `O_APPEND`).

## Kiến thức nền
Bạn được dùng **một trong hai** nhóm hàm làm việc với tệp (bộ chấm không phân biệt). Quy trình luôn là **mở → đọc/ghi
từng khối → đóng**, làm hai lần cho mỗi client (một lần với tệp câu chào, một lần với tệp log).

| | Cách 1: file descriptor (lab08) | Cách 2: `FILE *` (như `html.c`) |
|---|---|---|
| Đọc tệp câu chào | `fd = open(path, O_RDONLY)` | `f = fopen(path, "rb")` |
| Đọc từng khối | `n = read(fd, buffer, sizeof(buffer))` | `n = fread(buffer, 1, sizeof(buffer), f)` |
| Mở log ghi nối | `fd = open(path, O_WRONLY \| O_CREAT \| O_APPEND, 0644)` | `f = fopen(path, "ab")` |
| Ghi từng khối | `write(fd, buffer, n)` | `fwrite(buffer, 1, n, f)` |
| Đóng | `close(fd)` | `fclose(f)` |
| Mở lỗi | trả `-1` | trả `NULL` |

```c
// Cách 1
int gfd = open(argv[2], O_RDONLY);
if (gfd != -1) {
    while ((n = read(gfd, buffer, sizeof(buffer))) > 0) send(client, buffer, n, 0);
    close(gfd);
}
int lfd = open(argv[3], O_WRONLY | O_CREAT | O_APPEND, 0644);
while ((n = recv(client, buffer, sizeof(buffer), 0)) > 0) write(lfd, buffer, n);
close(lfd);

// Cách 2
FILE *f = fopen(argv[2], "rb");
if (f != NULL) {
    while ((n = fread(buffer, 1, sizeof(buffer), f)) > 0) send(client, buffer, n, 0);
    fclose(f);
}
FILE *log = fopen(argv[3], "ab");
while ((n = recv(client, buffer, sizeof(buffer), 0)) > 0) fwrite(buffer, 1, n, log);
fclose(log);
```

Lưu ý chung:
- Luôn xử lý đúng `n` byte vừa đọc/nhận (không `sizeof(buffer)`, không `strlen`: dữ liệu có thể chứa `0x00`).
- Log phải **ghi nối** (`O_APPEND` hoặc `"ab"`); `O_TRUNC` hoặc `"wb"` sẽ xoá dữ liệu client trước. `O_CREAT` để tạo tệp nếu chưa có.
- `fwrite` có bộ đệm nên phải `fclose`/`fflush` ngay khi xong một client; `write` thì vào tệp ngay.
- Đóng cả hai tệp mỗi client, nếu không sẽ hết 256 file descriptor.
