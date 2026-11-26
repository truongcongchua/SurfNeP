# Server ghi nối tiếp dữ liệu client vào tệp

Viết server chạy bằng:

```
./tcp_server <cổng> <tệp log>
```

Với **mỗi** client kết nối đến (phục vụ lần lượt từng client là đủ):

1. Nhận mọi dữ liệu client gửi đến và **ghi nối tiếp** vào cuối `<tệp log>` cho đến khi client đóng kết nối.
   Không ghi đè dữ liệu của client trước. Nếu tệp chưa tồn tại thì tạo mới; nếu đã có nội dung thì ghi tiếp vào cuối.
2. Xong một client thì dữ liệu phải **nằm trong tệp** ngay (`fclose` hoặc `fflush`), không đợi server kết thúc.
3. Server **không gửi** gì cho client. Đóng kết nối rồi quay lại `accept`.

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu client gửi là nhị phân bất kỳ (có byte `0x00`, không có `\n` cuối), có thể tới 100 KB, có thể đến thành
  nhiều mảnh nhỏ: ghi đúng từng byte `recv` trả về (đừng dùng `fputs`/`strlen`).
- Client không gửi gì thì log không được thêm byte nào (cũng không thêm `\n`).
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ `fclose` tệp log và
  `close` client mỗi lần).

## Ví dụ

```
$ ./tcp_server 9000 log.txt
```

Client 1 gửi `abc\n` rồi đóng. Client 2 gửi `xyz\n` rồi đóng. Khi đó `log.txt` chứa `abc\nxyz\n`.

## Kiến thức nền
Vòng `recv` đến khi trả `<= 0` như `tcp-echo`; mở tệp bằng `fopen(path, "ab")` (append) và `fwrite(buffer, 1, n, f)` với
`n` là số byte `recv` trả về. Bài này là nửa "ghi log" của `tcp-greeting-log`.
