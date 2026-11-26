# Server ghi log mọi message

Một yêu cầu riêng của bài tập lớn đặt vé máy bay (1 điểm): **server ghi lại mọi message nhận được và gửi đi**. Bài này
tách riêng phần đó với một giao thức tối thiểu để bạn tập trung vào việc ghi log.

Viết server TCP chạy bằng `./server <cổng> <tệp log>`, phục vụ **nhiều client cùng lúc** (ít nhất 30; `select` hoặc đa
luồng).

## Giao thức (một dòng mỗi lệnh)

Mỗi lệnh là một dòng kết thúc `\n` (bỏ **một** `\r` cuối dòng nếu có, tối đa 1000 byte). Server không chào khi client kết nối.

| Lệnh | Phản hồi |
|---|---|
| `PING` | `100 OK PONG` |
| `QUIT` | `100 OK` rồi đóng kết nối |
| mọi thứ khác (kể cả dòng trống) | `999 UNKNOWN ERROR` |

## Tệp log

Mỗi **sự kiện** ghi đúng **một dòng**, theo thứ tự xảy ra:

```
[2026-11-26 14:03:05] CONNECT 127.0.0.1:53122
[2026-11-26 14:03:05] RECV 127.0.0.1:53122 "PING"
[2026-11-26 14:03:05] SEND 127.0.0.1:53122 "100 OK PONG"
[2026-11-26 14:03:07] DISCONNECT 127.0.0.1:53122
```

- Dấu thời gian là giờ **địa phương** của server: `[YYYY-MM-DD HH:MM:SS]` (`time`, `localtime`, `strftime`).
- `127.0.0.1:53122` là địa chỉ và cổng **của client** (cổng theo thứ tự byte của máy, không phải của mạng).
- `CONNECT`: ngay khi chấp nhận kết nối. `DISCONNECT`: khi kết nối kết thúc, dù do `QUIT`, client đóng, hay mất kết nối đột ngột.
- `RECV`: mỗi **lệnh đủ một dòng** nhận được, in nội dung đã bỏ `\n` và `\r` cuối, đặt trong dấu nháy kép (không thoát ký tự
  bên trong). Lệnh bị cắt thành nhiều lần `recv` vẫn chỉ ghi **một** dòng `RECV`; nhiều lệnh dính nhau ghi mỗi lệnh một dòng.
  Phần dở dang không có `\n` khi client rời đi **không** được ghi.
- `SEND`: mỗi **dòng phản hồi** gửi đi, nội dung bỏ `\n`, đặt trong nháy kép.
- Thứ tự cho từng client luôn là `CONNECT`, rồi lặp (`RECV`, `SEND`), rồi `DISCONNECT`.
- Ghi log **trước khi** gửi phản hồi và **ghi ngay** ra tệp (`fflush`): bộ chấm đọc tệp ngay khi nhận được phản hồi và phải
  thấy dòng `RECV`/`SEND` tương ứng.
- Mở tệp log ở chế độ **nối** (`"a"`): không xóa nội dung đã có.

## Ví dụ

Client kết nối, gửi `PING\r\n`, gửi `HELLO\n`, rồi `QUIT\n`:

```
[2026-11-26 14:03:05] CONNECT 127.0.0.1:53122
[2026-11-26 14:03:05] RECV 127.0.0.1:53122 "PING"
[2026-11-26 14:03:05] SEND 127.0.0.1:53122 "100 OK PONG"
[2026-11-26 14:03:06] RECV 127.0.0.1:53122 "HELLO"
[2026-11-26 14:03:06] SEND 127.0.0.1:53122 "999 UNKNOWN ERROR"
[2026-11-26 14:03:07] RECV 127.0.0.1:53122 "QUIT"
[2026-11-26 14:03:07] SEND 127.0.0.1:53122 "100 OK"
[2026-11-26 14:03:07] DISCONNECT 127.0.0.1:53122
```

## Ràng buộc và bộ chấm kiểm tra
- Các dòng log của nhiều client được **xen kẽ** nhưng mỗi dòng phải nguyên vẹn (không trộn ký tự của hai dòng).
- Giờ trong log lệch không quá 2 giây so với giờ thật.
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng chục lệnh dính nhau; dữ liệu có thể chứa byte lạ (không có `0x00`).
- Client có thể mất kết nối đột ngột; bộ chấm chạy 300 lượt kết nối-ngắt với giới hạn 256 file descriptor, nên nhớ `close`.
  Giữ tệp log mở suốt thời gian chạy (không mở lại cho mỗi dòng).

## Kiến thức nền
`fopen("a")`, `fprintf`, `fflush` (lab07); `accept` với tham số địa chỉ rồi `inet_ntoa`, `ntohs` (`udp_receiver.c`);
`time`, `localtime`, `strftime` là thư viện C chung.
