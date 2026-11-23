# Chào từng client

Bài khởi động thứ hai: thêm **vòng lặp `accept`** và hàm **`send`**. Vẫn chưa cần `recv`.

Viết server chạy bằng `./server <cổng>`. Với **mỗi** client kết nối tới (phục vụ lần lượt từng client là đủ):

1. Gửi đúng một dòng chào `Hello, client <k>!` kèm `\n`, trong đó `<k>` là **số thứ tự** của client: client đầu tiên là `1`, client tiếp theo là `2`, ...
2. Đóng kết nối với client đó.
3. Quay lại `accept` chờ client tiếp theo.

Server **không bao giờ thoát**.

## Hàm mới cần dùng

| Hàm | Làm gì |
|---|---|
| `sprintf(message, "Hello, client %d!\n", count)` | ghép câu chào vào mảng ký tự `message` |
| `send(client, message, strlen(message), 0)` | gửi `strlen(message)` byte cho client |
| `close(client)` | đóng socket **của client** (không đóng socket nghe) |

Khung chung:

```c
int count = 0;
while (0 == 0) {
    int client = accept(listener, NULL, NULL);
    // ... đếm, ghép câu chào, send, close(client)
}
```

## Ràng buộc và bộ chấm kiểm tra
- Câu chào đúng từng ký tự: `Hello, client 1!\n`, không thêm byte `'\0'` (nên gửi `strlen(message)` byte, không phải `strlen + 1`).
- Số thứ tự tăng dần theo thứ tự `accept`, kể cả khi số có nhiều chữ số (`Hello, client 300!`).
- Client không gửi gì: server **không** `recv`, chào ngay sau khi `accept`.
- Sau mỗi câu chào, client phải thấy kết nối **bị đóng**.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra. Quên `close(client)` thì mỗi client để lại một fd và server sẽ hết fd.
- Có client kết nối rồi đóng ngay mà không đọc: server vẫn chào, vẫn tính số thứ tự và phục vụ tiếp client sau.

## Ví dụ

```
client 1 kết nối  →  nhận "Hello, client 1!\n", rồi bị đóng
client 2 kết nối  →  nhận "Hello, client 2!\n", rồi bị đóng
```

## Bẫy thường gặp
- Quên `close(client)`: sau khoảng 250 client server không `accept` được nữa.
- Đặt `count` **trong** vòng lặp (`int count = 0;` mỗi vòng): client nào cũng là số 1.
- Gọi `close(listener)` trong vòng lặp: client thứ hai không kết nối được.
- Thoát (`return`/`exit`) sau client đầu tiên.

## Kiến thức nền
`2-Chap2/tcp_server.c` (hàm `send`, `close`) và `3-Chap3/L2-LoopingServer/html.c` (vòng lặp `accept` không bao giờ thoát).
