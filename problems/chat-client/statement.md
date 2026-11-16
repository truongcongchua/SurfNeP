# Chat client dùng poll

Phía **client** của các bài chat: vừa đọc bàn phím để gửi, vừa nhận tin từ server để in ra, trong
**một tiến trình, một luồng** (không `fork`, không `pthread`). Dùng `poll()` (hoặc `select()`).

```
./chat_client <địa chỉ IP> <cổng>
```

## Yêu cầu
- Kết nối TCP tới server. Không kết nối được: in lỗi ra `stderr`, thoát với mã **khác 0**.
- Đồng thời theo dõi **stdin** và **socket**:
  - Có dữ liệu từ stdin → gửi ngay cho server (giữ nguyên từng byte, kể cả `\n`).
  - Có dữ liệu từ server → ghi ngay ra **stdout**, giữ nguyên từng byte. Không được đợi người dùng gõ gì.
- stdin kết thúc (EOF, `Ctrl+D`): báo cho server biết bạn không gửi nữa bằng `shutdown(fd, SHUT_WR)`, rồi
  **tiếp tục nhận** cho tới khi server đóng kết nối, sau đó thoát với mã `0`.
- Server đóng kết nối (khi stdin vẫn còn mở): thoát ngay với mã `0`.

Client này không cần biết giao thức chat: nó chỉ chuyển byte hai chiều. Bạn có thể thử nó với server của bài
*chat-select* / *chat-poll* của chính mình.

## Bộ chấm kiểm tra
Bộ chấm dựng server giả, chạy chương trình của bạn với stdin là pipe và stdout là tệp, rồi kiểm tra:
tin từ server phải hiện ra stdout **trong lúc stdin đang im lặng**, tin từ stdin phải đến server
**trong lúc server đang im lặng**, hai chiều xen kẽ không mất byte, và các trường hợp đóng kết nối.

## Bẫy hay gặp
- Gọi `fgets(stdin)` rồi mới `recv()` (hoặc ngược lại): bị chặn ở một phía, phía kia "đơ".
- `printf` ra stdout khi stdout là **tệp/pipe** thì được đệm đầy (full buffering): dữ liệu chỉ hiện khi thoát.
  Hãy dùng `write(1, ...)` hoặc `fflush(stdout)` sau mỗi lần in.
- `poll()` báo `POLLIN` trên stdin cả khi gặp EOF (`read` trả `0`): phải ngừng theo dõi stdin, nếu không
  sẽ lặp vô hạn với CPU 100%.
- `recv` trả `0` nghĩa là server đã đóng.
