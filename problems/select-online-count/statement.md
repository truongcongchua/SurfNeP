# Đếm client đang kết nối bằng select

Viết server `./server <cổng>` **một tiến trình, một luồng**, dùng **`select()`** phục vụ nhiều client cùng lúc:

- Khi một client kết nối, server gửi cho nó đúng một dòng `ONLINE <n>\n`, trong đó `n` là **số client đang kết nối
  tại thời điểm đó, tính cả client này** (client đầu tiên: `ONLINE 1`).
- Dữ liệu client gửi lên được **đọc rồi bỏ đi**: server không trả lời, không in gì.
- Client đóng kết nối (kể cả chỉ `shutdown` chiều gửi, hay bị reset) thì server `close` socket của client đó, và
  client đó không còn được tính vào `n` của những người đến sau.
- Server chạy mãi, không giới hạn số client nào ngoài 50 client cùng lúc của bộ chấm.

**Không được dùng:** `fork`, `pthread`, `poll`, `epoll`. Bộ chấm kiểm tra điều này (verdict `CV`).

## Bài này để làm gì
Bước khởi động cho `select-echo`. `select-two-ports` luyện `fd_set`/`max_fd`/`FD_ISSET` với số fd cố định. Bài này
luyện nửa còn lại: **danh sách client thay đổi** (thêm khi `accept`, xoá khi `recv <= 0`). Vì chỉ đọc-và-bỏ, chưa có
gửi trả dữ liệu như `select-echo`:

| Kỹ thuật dùng ở `select-echo` | Làm ở bài này |
|---|---|
| Mảng `client_list[]`, thêm khi `accept` | `n` là `number_of_clients` sau khi thêm |
| Dựng lại `fd_set` từ mảng mỗi vòng, `max_fd` gồm cả client | Vòng đời của nhiều client mở/đóng xen kẽ |
| `recv` trả `0` hoặc `-1` thì `close(fd)` **và** xoá khỏi mảng (code mẫu gốc quên bước xoá) | Không xoá thì `n` không bao giờ giảm |
| Quên `close` là hết 256 fd | Test 300 client |

## Ràng buộc và bộ chấm kiểm tra
- Tới 50 client cùng lúc. Mảng client của bạn cần ít nhất 50 phần tử (có thể lớn hơn).
- Client có thể gửi dữ liệu tới vài trăm KB mà không đọc gì ngoài dòng `ONLINE`: server phải đọc hết (không để đầy
  bộ đệm) và **không gửi lại** byte nào.
- Sau khi một client đóng, bộ chấm đợi khoảng 0,15 giây trước khi cho client mới vào.
- Client có thể bị reset (RST) khi server không còn gì phải gửi cho nó.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra.
- Dòng chào đúng dạng `ONLINE <n>\n`, một dấu cách, `n` viết bằng số thập phân.

## Ví dụ

```
A kết nối            → A nhận "ONLINE 1\n"
B kết nối            → B nhận "ONLINE 2\n"
A đóng kết nối
C kết nối            → C nhận "ONLINE 2\n"   (B và C)
```

## Gợi ý
- Khung là `select_server.c` bỏ phần `send` lại: mảng `client_list[]`, `number_of_clients`, vòng `FD_ZERO`/`FD_SET`.
- Gửi chào bằng `sprintf(message, "ONLINE %d\n", number_of_clients);` rồi `send(fd, message, strlen(message), 0)`.
- Khi `recv` trả `<= 0`: `close(fd)`, rồi đưa phần tử cuối vào chỗ trống, `number_of_clients--`, `i--`.
