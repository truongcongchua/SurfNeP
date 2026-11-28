# Một server, hai cổng, dùng select

Viết server `./server <cổng>` **một tiến trình, một luồng** mở **hai** socket nghe cùng lúc: cổng `<cổng>` và cổng
`<cổng> + 1`. Dùng **`select()`** để chờ cả hai.

- Client kết nối vào `<cổng>` nhận `ONE\n` (4 byte), client kết nối vào `<cổng> + 1` nhận `TWO\n` (4 byte).
- Gửi xong thì server đóng kết nối với client đó và quay lại chờ. Server không đọc gì từ client và chạy mãi.

**Không được dùng:** `fork`, `pthread`, `poll`, `epoll`. Bộ chấm kiểm tra điều này (verdict `CV`).

## Bài này để làm gì
Bước khởi động cho `select-echo`. Chỉ giữ lại phần "dựng `fd_set` rồi gọi `select`" và bỏ phần quản lý danh sách client
(phần đó nằm ở `select-online-count`). Đây là bài có số fd cố định (hai socket nghe), nên mọi lỗi nếu có đều nằm ở
cách dùng `select`:

| Kỹ thuật dùng ở `select-echo` | Làm ở bài này |
|---|---|
| `FD_ZERO` rồi `FD_SET` lại **mỗi vòng** vì `select` ghi đè tập | Dựng lại cả hai listener mỗi vòng |
| `max_fd` là fd lớn nhất, tham số đầu của `select` là **`max_fd + 1`** | Hai fd khác nhau, fd thứ hai thường lớn hơn |
| `FD_ISSET(fd, &read_fds)` cho biết fd nào sẵn sàng; `accept` lúc đó không chặn | Hai lệnh `if (FD_ISSET(...))` độc lập |
| Một luồng không được chặn ở một fd trong khi fd khác đang chờ | Client ở cổng 2 không được chờ client ở cổng 1 |
| `close(client)` sau khi xong, không đóng socket nghe | Test 300 client với giới hạn 256 fd |

## Ràng buộc và bộ chấm kiểm tra
- Tới 30 client cùng lúc ở mỗi cổng. Dùng `listen(.., 64)` cho cả hai socket nghe.
- Client ở cổng này có thể không bao giờ xuất hiện trong khi cổng kia đông: cả hai thứ tự đều được thử.
- Client có thể đóng kết nối ngay khi vừa kết nối; server không được thoát vì chuyện đó.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra.
- Không in gì ra stdout.

## Ví dụ

```
./server 5000        (nghe 5000 và 5001)
client kết nối 5001  → nhận "TWO\n", bị đóng
client kết nối 5000  → nhận "ONE\n", bị đóng
```

## Gợi ý
- Mẫu giống `select_server.c`, nhưng thay vòng `for` theo `client_list` bằng hai lệnh `FD_SET` cố định:
  ```c
  FD_ZERO(&read_fds);
  FD_SET(listener1, &read_fds);
  FD_SET(listener2, &read_fds);
  int max_fd = listener1 > listener2 ? listener1 : listener2;
  select(max_fd + 1, &read_fds, NULL, NULL, NULL);
  ```
- Sau `select`, kiểm tra **từng** listener bằng `if (FD_ISSET(...))` (đừng `else if`: cả hai có thể cùng sẵn sàng).
- Viết hàm `make_listener(int port)` gồm `socket` → `setsockopt(SO_REUSEADDR)` → `bind` → `listen` rồi gọi hai lần.
  Dựng `fd_set` một lần trước vòng lặp là sai: `select` đã xoá các fd chưa sẵn sàng khỏi nó.
