# Echo server dùng select

Viết echo server `./server <cổng>` giống bài *tcp-echo*: gửi trả nguyên vẹn mọi byte nhận được.
Khác biệt là server phải phục vụ **đồng thời** nhiều client (tối thiểu 50) trong **một tiến trình,
một luồng**, bằng **`select()`**.

**Không được dùng:** `fork`, `pthread`, `poll`, `epoll`. Bộ chấm kiểm tra điều này (verdict `CV`).

## Bài khởi động
Nếu chưa quen `select`, làm hai bài này trước. Mỗi bài luyện một nửa của bài này và dễ hơn nó:

| Bài | Luyện | Dùng lại ở bài này |
|---|---|---|
| `select-two-ports` | Dựng `fd_set` mỗi vòng, `max_fd + 1`, `FD_ISSET` cho từng socket nghe, `accept` không chặn, một luồng phục vụ hai nguồn | Khung vòng lặp `select` |
| `select-online-count` | Mảng `client_list[]`: thêm khi `accept`, `close` **và** xoá khi `recv <= 0`, đọc dữ liệu client | Quản lý danh sách client. Phần còn lại ở bài này là `send` trả đúng dữ liệu (luồng byte lớn, bộ đệm đầy) |

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể ngừng gửi (`shutdown`) rồi chờ đọc: server phải gửi trả **hết** rồi mới đóng.
- Client có thể gửi tới khi đầy bộ đệm rồi mới đọc: server phải gửi đủ, không được bỏ client.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc, gửi xen kẽ theo thứ tự ngẫu nhiên; client im lặng không được làm treo client khác.

## Kiến thức nền
Lecture notes §3.5: `fd_set` bị `select` **ghi đè**, nên phải dựng lại mỗi vòng lặp; tham số đầu
là `maxfd + 1`; khi `recv` trả về 0 thì `close` và bỏ fd khỏi danh sách.
