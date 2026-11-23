# Server non-blocking không dùng select

Viết echo server `./server <cổng>` giống bài *tcp-echo*, phục vụ **đồng thời** tối thiểu 50 client
trong một tiến trình, một luồng, chỉ bằng **socket non-blocking**: đặt chế độ non-blocking bằng
`ioctl(fd, FIONBIO, &io_mode)` như code mẫu, rồi **liên tục thử** `accept`/`recv`.

**Không được dùng:** `select`, `poll`, `epoll`, `fork`, `pthread`.

## Yêu cầu
- Đặt non-blocking cho **cả** socket lắng nghe **và** từng socket client vừa `accept`.
- Phân biệt ba kết quả của `recv` trên socket non-blocking:
  `> 0` có dữ liệu → gửi lại; `0` client đóng → `close` **và xoá khỏi mảng**; `-1` **chưa có dữ liệu**
  (không phải lỗi!) → bỏ qua, thử client tiếp theo.
- Nên xoá client đã đóng khỏi mảng (code mẫu `non_blocking_server.c` chỉ `close` mà vẫn giữ nó trong
  `client_sockets`, nên mảng cứ dài mãi).

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu là **luồng byte** bất kỳ (kể cả `0x00`), đến thành mảnh ngẫu nhiên hoặc dính thành khối lớn (tới 1 MB).
- Client có thể ngừng gửi (`shutdown`) rồi chờ đọc: server phải gửi trả **hết** rồi mới đóng.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client lần lượt vào-ra
  (quên `close()` là hết fd).
- Tới 50 client cùng lúc, gửi xen kẽ theo thứ tự ngẫu nhiên; client im lặng không được làm treo client khác.
- Bộ chấm **không** thử trường hợp client gửi dồn mà không đọc: trên socket non-blocking, `send` khi bộ đệm
  gửi đầy sẽ bỏ dở (đây là một lý do người ta chuyển sang `select`).

## Kiến thức nền
Lecture notes §3.1; code mẫu `non_blocking_server.c`. Sau bài này, hãy so sánh với *select-echo*
để thấy vì sao cần cơ chế ghép kênh.
