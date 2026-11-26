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
  không thừa không thiếu (đừng dùng `fgets`/`strlen`).
- Chương trình chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt (nhớ `fclose` tệp và `close`
  client mỗi lần).

## Ví dụ

```
$ cat data.txt
Xin chao!
$ ./tcp_server 9000 data.txt
```

Mỗi client kết nối đến nhận `Xin chao!\n` rồi bị đóng kết nối.

## Kiến thức nền
`fopen` chế độ `"rb"`, vòng `fread` → `send` như `html.c`. Gửi đúng số byte `fread` trả về, không phải `sizeof(buffer)`.
Bài này là nửa "gửi câu chào từ tệp" của `tcp-greeting-log`.
