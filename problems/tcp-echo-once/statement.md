# Echo một lần

Bài khởi động thứ ba, và là bước ngay trước bài *tcp-echo*: thêm **`recv`**. Đây chính là `tcp_server.c` trên lớp.

Viết server chạy bằng `./server <cổng>`:

1. `socket` → `bind` → `listen` → `accept` **một** client (như bài *tcp-accept-close*).
2. Gọi `recv` **một lần** để nhận dữ liệu client gửi.
3. Gọi `send` gửi lại **đúng số byte** vừa nhận được.
4. Đóng socket của client và socket nghe, rồi thoát với mã `0`.

## Hàm mới cần dùng

| Hàm | Làm gì | Trả về |
|---|---|---|
| `recv(client, buffer, sizeof(buffer), 0)` | nhận dữ liệu vào `buffer`; chờ tới khi có dữ liệu | số byte nhận được; `0` nếu client đã đóng; `-1` nếu lỗi |
| `send(client, buffer, bytes_received, 0)` | gửi `bytes_received` byte đầu của `buffer` | số byte đã gửi, hoặc `-1` nếu lỗi |

```c
char buffer[1024];
int bytes_received = recv(client, buffer, sizeof(buffer), 0);
if (bytes_received == -1) {
    perror("recv");
    close(client);
    close(listener);
    exit(EXIT_FAILURE);
}
send(client, buffer, bytes_received, 0);   // gửi đúng bytes_received byte
```

## Ràng buộc và bộ chấm kiểm tra
- Mỗi client gửi tối đa **1000 byte**, gửi trong **một** lần; dữ liệu có thể là byte bất kỳ, kể cả `0x00`.
- Server chỉ `recv` **một lần** và `send` lại đúng dữ liệu đó, không thêm không bớt; sau đó đóng kết nối.
- Client có thể chưa gửi ngay: server phải **chờ ở `recv`**, không được gửi gì trước khi nhận.
- Client có thể kết nối rồi đóng luôn mà không gửi gì (`recv` trả về `0`): server vẫn đóng gọn gàng và thoát mã `0`, không treo.
- Server chỉ phục vụ một client rồi kết thúc với mã `0`.

## Ví dụ

```
client gửi: "xin chao\n"    →  server gửi lại: "xin chao\n", rồi đóng kết nối
client gửi 3 byte 00 FF 41  →  server gửi lại: 00 FF 41, rồi đóng kết nối
```

## Bẫy thường gặp
- Dùng `strlen(buffer)` làm độ dài khi `send`: `buffer` không có `'\0'` ở cuối và có thể có `0x00` ở giữa. Dùng **số byte `recv` trả về**.
- Gửi `sizeof(buffer)` byte: gửi cả phần rác chưa được ghi.
- In `buffer` bằng `printf("%s")` rồi gửi lại: chỉ đúng với văn bản, sai với dữ liệu nhị phân.

## Kiến thức nền
`2-Chap2/tcp_server.c`: bài này viết lại đúng file đó (cổng lấy từ dòng lệnh thay vì cố định 8080).

Bài *tcp-echo* sau đó chỉ thêm đúng **hai vòng lặp**: một vòng `accept` để phục vụ nhiều client lần lượt, một vòng `recv` → `send` để echo cho tới khi client đóng.
