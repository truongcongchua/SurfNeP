# Thông báo thay đổi chuyến bay (trễ, đổi lịch, hủy)

Chức năng "nhận thông báo về các chuyến bay: thay đổi lịch trình, hủy chuyến, trễ chuyến" (3 điểm) của bài tập lớn đặt vé máy bay. Giống
phòng chat ở §4.3 có thêm "chủ phòng" (`OP`, `KICK`: lệnh chỉ chủ phòng được dùng): ở đây có **admin** (nhân viên hãng) ra lệnh, và
server **chủ động đẩy** thông báo tới đúng những khách có vé trên chuyến đó, kể cả khách **chưa đăng nhập lúc xảy ra sự kiện**
(thông báo được giữ lại và giao ngay khi họ đăng nhập).

Viết `./server <cổng> <khóa admin>`; phục vụ nhiều client cùng lúc (`select` hoặc `pthread`, nhớ mutex).

## Tệp (nạp khi khởi động, thay đổi chỉ cần giữ trong bộ nhớ)
- `accounts.txt`: `<user> <pass>`.
- `flights.txt`: như các bài trước (mã chuyến duy nhất).
- `tickets.txt`: `<số vé> <user> <chuyến> <ngày> <hạng> <hành khách> <giá> <trạng thái>`; chỉ vé `PAID` mới được thông báo.

## Lệnh (mỗi lệnh một dòng `\n`, bỏ `\r` cuối, các thành phần cách nhau đúng một dấu cách)

Server không chào khi client kết nối.

| Lệnh | Phản hồi |
|---|---|
| `LOGIN <user> <pass>` | `201 INVALID` (không đúng 3 thành phần), `207 ALREADY LOGGED IN` (phiên này đã đăng nhập), `203 DENIED` (sai tên/mật khẩu), `100 OK <user>`. Một tài khoản đăng nhập được ở nhiều phiên |
| `ADMIN <khóa>` | `100 OK` nếu đúng khóa (phiên thành admin, có thể gọi nhiều lần), `203 DENIED` nếu sai, `201 INVALID` nếu sai số thành phần |
| `STATUS <chuyến>` | `100 OK ON_TIME` / `100 OK DELAYED <phút>` / `100 OK RESCHEDULED <ngày> <giờ đi> <giờ đến>` / `100 OK CANCELLED`; không có chuyến `202 NOT FOUND`; sai số thành phần `201 INVALID` |
| `DELAY <chuyến> <phút>` | **chỉ admin** |
| `RESCHEDULE <chuyến> <ngày> <giờ đi> <giờ đến>` | **chỉ admin** |
| `CANCELFLIGHT <chuyến>` | **chỉ admin** |
| `QUIT` | `100 OK` rồi đóng |
| mọi thứ khác | `999 UNKNOWN ERROR` |

**Lệnh admin** kiểm tra theo thứ tự: phiên chưa phải admin → `203 DENIED` (kể cả khi lệnh sai cú pháp); sai số thành phần hoặc định dạng → `201
INVALID`; không có chuyến → `202 NOT FOUND`; chuyến đã hủy → `209 ALREADY CANCELLED`. Định dạng: `phút` là số thập phân từ 1 đến 1440 không
có số 0 đứng đầu; `ngày` là ngày thật `YYYY-MM-DD`; `giờ` là `HH:MM` hợp lệ (`00:00`–`23:59`; giờ đến nhỏ hơn giờ đi nghĩa là sang hôm sau, vẫn hợp lệ).
Lệnh thành công cập nhật trạng thái chuyến (`DELAY` → `DELAYED <phút>` thay cho trạng thái trước; `RESCHEDULE` → `RESCHEDULED ...` thay cho trạng
thái trước; `CANCELFLIGHT` → `CANCELLED`), gửi thông báo, rồi trả `100 OK <k>` với `k` là **số khách khác nhau** có vé `PAID` trên chuyến đó
(dù đang online hay không).

## Thông báo (server chủ động gửi)

| Sự kiện | Dòng gửi cho khách |
|---|---|
| `DELAY` | `301 NOTIFY DELAY <chuyến> <phút>` |
| `RESCHEDULE` | `301 NOTIFY RESCHEDULE <chuyến> <ngày> <giờ đi> <giờ đến>` |
| `CANCELFLIGHT` | `301 NOTIFY CANCEL <chuyến>` |

- Nhận thông báo: **mọi phiên** đang đăng nhập bằng tài khoản có vé `PAID` trên chuyến đó, mỗi phiên **một** dòng (dù tài khoản có nhiều vé
  trên chuyến đó). Phiên admin chỉ nhận nếu bản thân nó đăng nhập bằng một tài khoản như vậy.
- Tài khoản **không có phiên nào đang đăng nhập** lúc sự kiện: thông báo được **xếp hàng** theo thứ tự xảy ra. Ngay sau khi gửi `100 OK <user>`
  cho lần `LOGIN` thành công kế tiếp, server gửi toàn bộ hàng đợi (theo thứ tự) rồi xóa hàng đợi. Nếu tài khoản đã có phiên khác đang online,
  `LOGIN` thêm một phiên **không** nhận lại thông báo cũ.
- Thông báo được gửi tới các khách **trước khi** admin nhận `100 OK <k>`.
- Phiên rời đi (kể cả đột ngột) thì không còn nhận thông báo; tài khoản coi như offline nếu không còn phiên nào.

## Ví dụ (khóa `admin-2026`; `an` và `binh` có vé trên `VN100`, `chi` thì không)

```
A: LOGIN an 1234           ← 100 OK an
C: ADMIN admin-2026        ← 100 OK
C: DELAY VN100 45          ← (A nhận) 301 NOTIFY DELAY VN100 45
                           ← (C nhận) 100 OK 2              (an và binh; binh đang offline nên được xếp hàng)
B: LOGIN binh abcd         ← 100 OK binh
                           ← 301 NOTIFY DELAY VN100 45      (hàng đợi giao ngay sau 100 OK)
A: STATUS VN100            ← 100 OK DELAYED 45
```

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu thật là các tệp của bộ chấm (6 chuyến, 5 tài khoản, 10 vé; có vé `CANCELLED`, tài khoản nhiều vé trên cùng chuyến, chuyến có 3 khách).
- Nhiều thông báo liên tiếp phải đến **đúng thứ tự**, và thông báo xen giữa phản hồi của lệnh khác vẫn đúng từng dòng.
- Một phiên của khách đã đóng ngay trước khi server đẩy tin: server **không được chết** (xem "Được phép dùng thêm").
- Lệnh có thể bị cắt vụn từng byte hoặc dính nhau; bộ chấm kiểm tra 300 lượt vào–ra với giới hạn 256 file descriptor.

## Kiến thức nền
§4.3 (thông điệp server chủ động gửi, lệnh chỉ dành cho chủ phòng), danh sách client như `pthread_chatroom.c`, hàng đợi (mảng hoặc danh sách liên kết)
theo từng tài khoản. **Được phép dùng thêm** (không bắt buộc): `signal(SIGPIPE, SIG_IGN)` hoặc cờ `MSG_NOSIGNAL` để server không chết khi `send` vào kết nối
đã đóng (xem thẻ "Hàm mạng ngoài code mẫu").
