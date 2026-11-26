# Phát hành vé điện tử (email SMTP và thông báo)

Sau khi thanh toán, khách "nhận mã vé điện tử qua email hoặc tin nhắn" (2 điểm của bài tập lớn). Bài này làm đúng khâu đó:
server phát hành vé, **gửi email thật qua SMTP** (server đóng vai **client** của một máy chủ mail) và **đẩy tin nhắn** cho các
phiên khác đang đăng nhập cùng tài khoản.

SMTP không có trong bài giảng nhưng cùng kiểu với POP3 (§4.2.3): lệnh text một dòng, server trả lời bằng **mã ba chữ số**. Đề cho
sẵn đủ các lệnh cần dùng bên dưới. Viết `./server <cổng> <ip SMTP> <cổng SMTP>`; phục vụ nhiều client cùng lúc (`select` hoặc
`pthread`).

## Tệp

- `accounts.txt`: mỗi dòng `<user> <pass> <email>`, nạp khi khởi động.
- `tickets.txt`: mỗi dòng một vé đã phát hành `<số vé> <user> <chuyến> <ngày> <hạng> <hành khách>`. Vé mới **ghi nối** vào cuối
  tệp ngay. Có sẵn vài dòng.

## Giao thức với client (mỗi lệnh một dòng `\n`, bỏ `\r` cuối, các thành phần cách nhau đúng một dấu cách)

Server không chào khi client kết nối.

| Lệnh | Phản hồi |
|---|---|
| `LOGIN <user> <pass>` | sai cú pháp `201 INVALID`; phiên đã đăng nhập `207 ALREADY LOGGED IN`; sai tên/mật khẩu `203 DENIED`; đúng `100 OK <user>`. Một tài khoản có thể đăng nhập ở **nhiều phiên** |
| `ISSUE <chuyến> <ngày> <hạng> <hành khách>` | phát hành vé (xem dưới) |
| `QUIT` | `100 OK` rồi đóng |
| mọi thứ khác | `999 UNKNOWN ERROR` |

`user`, `pass`: luật như bài *fly-auth*. Kiểm tra của `ISSUE`: chưa đăng nhập → `204 LOGIN FIRST` (trước cả cú pháp); sai số thành phần
hoặc sai định dạng → `201 INVALID`, gồm: `chuyến` = đúng 2 chữ cái in hoa + 1–4 chữ số; `ngày` = ngày thật `YYYY-MM-DD`; `hạng` =
`ECO` hoặc `BUS`; `hành khách` = 1–40 ký tự trong `A-Z a-z _`.

## Phát hành vé (`ISSUE` hợp lệ)

1. **Số vé** gồm 13 chữ số: 3 chữ số mã hãng theo hai chữ cái đầu của `chuyến` (`VN`→`738`, `VJ`→`978`, `QH`→`126`, `BL`→`550`,
   còn lại `000`) rồi **số thứ tự 10 chữ số** (đệm số 0 phía trước). Số thứ tự là `1 +` số dòng của `tickets.txt` lúc khởi động
   cho vé đầu tiên, rồi tăng 1 sau mỗi vé; hai vé không bao giờ trùng số thứ tự (kể cả khi nhiều phiên cùng `ISSUE`).
   Ví dụ `tickets.txt` có 2 dòng: vé `VN` đầu tiên là `7380000000003`.
2. Ghi nối vào `tickets.txt` dòng `<số vé> <user> <chuyến> <ngày> <hạng> <hành khách>`.
3. **Gửi email** tới địa chỉ của `user` qua SMTP (bên dưới). Chỉ chờ tối đa **2 giây cho mỗi phản hồi** của máy chủ mail.
4. Lưu bản sao thư vào `outbox/<user>/<số vé>.eml` (tạo thư mục bằng `mkdir`): đúng các byte của thư đã gửi (bên dưới), kết thúc
   dòng bằng `\r\n`, **không** kèm dòng `.` cuối.
5. **Đẩy tin nhắn** `300 TICKET <số vé>` tới mọi phiên **khác** đang đăng nhập cùng tài khoản (không gửi cho phiên đang `ISSUE`),
   **trước khi** trả lời phiên đang `ISSUE`.
6. Trả lời: `100 OK <số vé>` nếu email gửi thành công, hoặc `100 OK <số vé> MAIL_FAILED` nếu không gửi được (không kết nối được,
   máy chủ mail trả mã lạ, đóng giữa chừng, hoặc quá 2 giây không trả lời).

Vé **luôn được phát hành** dù gửi mail thất bại: các bước 1, 2, 4, 5 vẫn xảy ra (bản sao `.eml` là thư đã định gửi).

### Hội thoại SMTP (server = client của máy chủ mail; mỗi dòng kết thúc `\r\n`)

```
S (mail) → server : 220 <chào>                    ← đọc dòng chào, phải bắt đầu bằng 220
server → S        : HELO fly.local                ← phản hồi bắt đầu bằng 250
server → S        : MAIL FROM:<noreply@fly.local> ← 250
server → S        : RCPT TO:<email của user>      ← 250
server → S        : DATA                          ← 354
server → S        : <thư, mỗi dòng \r\n>
server → S        : .                              ← dòng chỉ có một dấu chấm, báo hết thư; phản hồi 250
server → S        : QUIT                           ← 221 (không cần chờ), rồi đóng kết nối
```

Phản hồi của SMTP có thể gồm **nhiều dòng**: các dòng đầu có dạng `250-...` (có dấu `-` ở vị trí thứ 4), dòng **cuối** có dạng
`250 ...` (dấu cách ở vị trí thứ 4). Phải đọc đến dòng cuối. Mã đầu tiên khác mã mong đợi (kể cả `550` cho `RCPT TO`) là thất bại:
gửi `QUIT`, đóng, và trả `MAIL_FAILED`.

Thư (đúng 7 dòng, mỗi dòng kết thúc `\r\n`):

```
From: noreply@fly.local
To: <email>
Subject: Ve dien tu <số vé>
(dòng trống)
Ticket: <số vé>
Flight: <chuyến> <ngày> <hạng>
Passenger: <hành khách>
```

## Ví dụ

```
A: LOGIN an 1234                      ← 100 OK an
B: LOGIN an 1234                      ← 100 OK an        (cùng tài khoản, phiên khác)
A: ISSUE VN213 2026-12-20 ECO NGUYEN_VAN_AN
     (server nói chuyện SMTP với máy chủ mail ...)
B nhận:                               ← 300 TICKET 7380000000003
A nhận:                               ← 100 OK 7380000000003
```

## Ràng buộc và bộ chấm kiểm tra
- Bộ chấm đóng vai máy chủ SMTP tại `127.0.0.1:2525`: có lúc trả lời nhiều dòng `250-`, trả `550` cho `RCPT TO`, đóng kết nối giữa
  chừng, im lặng không trả lời, hoặc không chạy (kết nối bị từ chối). Server của bạn vẫn phải trả lời client và **không sập**.
- Bộ chấm kiểm tra từng byte của hội thoại SMTP, của `.eml` và của `tickets.txt`.
- Một client đã đóng kết nối ngay trước khi server đẩy tin cho nó: server **không được chết** (gợi ý bên dưới).
- Lệnh có thể bị cắt vụn từng byte, hoặc nhiều lệnh dính nhau.

## Kiến thức nền
`connect`/`send`/`recv` như client trong `tcp_client.c`; ghép dòng; ghi tệp (`fopen "a"`); thư viện C chung (`mkdir`, `sprintf`). Chờ phản
hồi có giới hạn thời gian: `select` với `struct timeval` (§3.5) trên socket SMTP.
**Được phép dùng thêm** (không bắt buộc): `signal(SIGPIPE, SIG_IGN)` hoặc cờ `MSG_NOSIGNAL` để server không chết khi `send` vào kết nối đã
đóng (xem thẻ "Hàm mạng ngoài code mẫu").
