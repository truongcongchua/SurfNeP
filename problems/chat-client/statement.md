# Chat client dùng select

Phía **client** của các bài chat: vừa đọc bàn phím để gửi, vừa nhận tin từ server để in ra, trong
**một tiến trình, một luồng** (không `fork`, không `pthread`). Dùng `select()` như code mẫu `select_client.c`.

```
./chat_client <địa chỉ IP> <cổng>
```

## Yêu cầu
- Kết nối TCP tới server (`inet_addr`, `connect`). Không kết nối được: in lỗi ra `stderr`, thoát với mã **khác 0**.
- Đồng thời theo dõi **stdin** và **socket** bằng `select`:
  - Có dữ liệu từ stdin → gửi ngay cho server (giữ nguyên từng byte, kể cả `\n`).
  - Có dữ liệu từ server → ghi ngay ra **stdout**, giữ nguyên từng byte. Không được đợi người dùng gõ gì.
- stdin kết thúc (EOF, `Ctrl+D`, tức `read` trả `0`): đóng kết nối và thoát với mã `0`.
- Server đóng kết nối (`recv` trả `0` hoặc `-1`): thoát ngay với mã `0`.

Client này không cần biết giao thức chat: nó chỉ chuyển byte hai chiều. Bạn có thể thử nó với server của bài
*chat-select* / *thread-chat* của chính mình.

## Ràng buộc
- Dữ liệu hai chiều là byte bất kỳ (có `0x00`, nửa dòng chưa có `\n`): chuyển ngay và nguyên vẹn.
- Khi cả hai phía đều im lặng, chương trình phải **ngủ** trong `select` (bộ chấm đo CPU: lặp bận 100% là trượt).
- Server có thể đóng thường, RST, hoặc đóng trong lúc stdin vẫn đổ dữ liệu: thoát mã 0, không treo.
  Server có thể dồn vài MB một lúc.

## Bộ chấm kiểm tra
Bộ chấm dựng server giả, chạy chương trình của bạn với stdin là pipe và stdout là tệp, rồi kiểm tra:
tin từ server phải hiện ra stdout **trong lúc stdin đang im lặng**, tin từ stdin phải đến server
**trong lúc server đang im lặng**, hai chiều xen kẽ không mất byte, và các trường hợp đóng kết nối.

## Bẫy hay gặp
- Gọi `fgets(stdin)` rồi mới `recv()` (hoặc ngược lại): bị chặn ở một phía, phía kia "đơ".
- `fgets` chờ tới khi có `\n` và dừng ở byte `0x00`; `printf("%s")` cũng dừng ở `0x00`. Hãy đọc stdin bằng
  `read(STDIN_FILENO, buffer, sizeof(buffer))` (lab08) và in bằng `fwrite(buffer, 1, n, stdout)`.
- `printf`/`fwrite` chỉ thực sự in khi gặp `\n`: tin dở dòng phải `fflush(stdout)` ngay.
- `select` ghi đè `fd_set`: `FD_ZERO` + `FD_SET` lại **mỗi vòng**; tham số đầu là `max_fd + 1`.
- Xét socket **trước** stdin trong mỗi vòng: server đã đóng thì thoát luôn, đừng gửi tiếp vào kết nối đã đóng.
