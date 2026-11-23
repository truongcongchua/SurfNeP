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
3. Ghi xong phần dữ liệu của một client thì dữ liệu phải **nằm trong tệp** ngay (`fflush`/`fclose`
   hoặc dùng `write`), không đợi server kết thúc.

## Ràng buộc và bộ chấm kiểm tra
- Câu chào có thể rỗng, lớn tới 300 KB, hoặc chứa dữ liệu nhị phân (byte `0x00`, không có `\n` cuối): gửi
  **đúng từng byte** (đừng dùng `fgets`/`strlen`). Tệp có thể bị thay đổi giữa hai client.
- Dữ liệu client gửi là nhị phân bất kỳ; client không gửi gì thì log không được thêm byte nào.
- Client có thể gửi dữ liệu trước khi đọc câu chào, gửi từng mảnh nhỏ, hoặc mất kết nối đột ngột (RST) sau khi
  đã nhận câu chào.
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ đóng cả tệp câu
  chào lẫn tệp log mỗi lần).

## Ví dụ

```
$ cat greeting.txt
Xin chao! Day la server IT4062.
$ ./tcp_server 9000 greeting.txt log.txt
```

Client 1 kết nối, nhận câu chào, gửi `abc\n` rồi đóng. Client 2 gửi `xyz\n` rồi đóng.
Khi đó `log.txt` chứa `abc\nxyz\n`.

## Kiến thức nền
Đọc/ghi tệp: `fopen` chế độ `"rb"`/`"ab"` (lab07); gửi tệp bằng vòng `fread` → `send` như `html.c`.
