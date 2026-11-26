# Thiết kế bộ bài phục vụ BTL "Ứng dụng đặt vé máy bay online"

> Trạng thái: **đã duyệt và đã triển khai đủ 16 bài** (26/11/2026). Mục "Ghi chú triển khai" ở cuối tệp liệt kê chỗ bài thật khác bản thiết kế.
> Nguồn kiến thức: lecture notes §2–§4 (đặc biệt §4.1–4.4 Thiết kế giao thức) và code mẫu
> `IT4062/` đến commit `3dd8aea` ("chatroom protocol", 23/11): `4-Chap4/http_server.c`,
> `4-Chap4/pthread_chatroom.c`, cùng Chap1–Chap3 như trước.

## 0. Nguyên tắc

1. **Mỗi bài = một mảnh của barem BTL.** Cùng một giao thức `FLY` xuyên suốt (mục 2), nên lời
   giải các bài ghép lại gần như thành khung server của BTL.
2. **Giới hạn theo code mẫu chỉ áp cho phần lập trình mạng.** Bảng đối chiếu ở mục 5.
   - **Phần mạng** (hàm socket, địa chỉ, `select`, đa tiến trình/đa luồng để phục vụ client): lời giải
     chuẩn và mọi test **bắt buộc** chỉ cần những gì có trong code mẫu và slide. Một số hàm mạng ngoài
     code mẫu được phép dùng **tùy chọn**; đề ghi rõ và thẻ kiến thức giải thích (mục 5.1).
   - **Phần C/thư viện chung** dùng thoải mái để BTL tốt nhất có thể: `time/localtime/strftime/mktime`,
     `rand/srand`, `qsort`, `isdigit/isalnum/toupper`, `strtol`, `mkdir`, `stat`…
   - Hệ quả cho thiết kế:
     - Log có **timestamp** `[YYYY-MM-DD HH:MM:SS]`.
     - Giữ chỗ chưa thanh toán **hết hạn sau T giây**. Server kiểm tra hạn ở mỗi lệnh và ở mỗi lần
       `select` hết timeout.
     - Mã đặt chỗ (PNR) là **6 ký tự ngẫu nhiên** `A–Z0–9` (`rand`), kiểm tra không trùng.
     - Hộp thư lưu theo thư mục `outbox/<user>/` (`mkdir`), sắp xếp bằng `qsort`.
     - Hủy/đổi vé tính phí theo **thời gian còn lại tới giờ bay** (`mktime` + `time`).
     - Thanh toán vẫn là **mô phỏng** (không có cổng thanh toán thật), nhưng đầy đủ hơn: số thẻ
       đúng Luhn, hạn `MM/YY` chưa qua (so với ngày hiện tại), CVV 3 chữ số; ví điện tử có số dư.
     - **Email thật qua SMTP**: server đóng vai client SMTP, chỉ dùng `connect/send/recv` đã học.
       Riêng SMTP là giao thức không có trong slide (slide có POP3 §4.2.3, cùng kiểu lệnh text).
       Đề sẽ ghi sẵn đủ các lệnh cần dùng. **Tin nhắn** = server chủ động đẩy một dòng tới client
       (đúng mục "thông điệp server chủ động gửi" §4.3).
3. **Bài khởi động** theo đúng tiêu chí đã chốt: tách đúng một kỹ năng mà bài đích dùng, dễ hơn
   bài đích, không trùng nhau, không khoan lại kỹ năng đã có bài.
4. Bài mới gắn `chapter: 4` nếu kỹ năng chính là giao thức (§4), `chapter: 3` nếu là đồng thời.
   Bài nào hữu ích cho thi giữa kỳ (dạng "server TCP/UDP tối đa N client") được đánh dấu ⭐.

## 1. Barem BTL → bài luyện

| Mục barem | Điểm | Bài luyện (mới **đậm**, cũ thường) |
|---|---|---|
| Kết nối client–server bằng socket | 2 | đã đủ: tcp-echo, select-echo, thread-echo, chat-client |
| Ghi log message gửi/nhận ở server | 1 | **fly-log** |
| Đăng ký, đăng nhập | 2 | **fly-parse** (khởi động), **fly-auth** ⭐ |
| Tìm kiếm chuyến bay theo tiêu chí | 2 | **flight-filter** (khởi động), **fly-search** |
| So sánh giá vé, thời gian bay | 2 | **fly-compare** |
| Đặt vé và thanh toán | 3 | **fly-book** ⭐ |
| Nhận mã vé điện tử (email/tin nhắn) | 2 | **fly-eticket** |
| Quản lý vé: xem, hủy, đổi, in | 3 | **fly-manage**, **fly-print-client** |
| Thông báo chuyến bay: đổi lịch, hủy, trễ | 3 | **chat-proto** (khởi động, BT 4.1), **fly-notify** |
| Giao diện | 3 | **fly-client** (giao diện console có menu) |
| Tính năng nâng cao | 5 | **fly-web** (giao diện web theo `http_server.c`), **fly-status-udp** ⭐ |
| (Ôn giữa kỳ) | — | **mock-flight-tcp** ⭐ — Thi thử 3, 90 phút, test ẩn |

Tổng: **16 bài mới**. Không thêm bài cho mục "kết nối socket" vì 34 bài hiện có đã phủ.

## 2. Giao thức FLY dùng chung (theo §4.3)

Trả lời 6 câu hỏi thiết kế của §4.3:

| Câu hỏi §4.3 | Lựa chọn |
|---|---|
| Text hay binary? | **Text**, mỗi thông điệp một dòng `\n` (bỏ `\r` cuối), tối đa 1000 byte |
| Server bị động hay chủ động? | **Chủ động**: có thông điệp đẩy `3xx` (vé điện tử, thông báo chuyến bay) |
| Xử lý từng yêu cầu hay nhiều? | Lần lượt từng dòng; nhiều dòng dính nhau trong một `recv` phải tách đúng |
| Theo phiên? | **Có**: trạng thái chưa đăng nhập / đã đăng nhập / admin theo từng kết nối |
| Xác thực? | `LOGIN user pass`, tài khoản lưu ở `accounts.txt` |
| Bảo mật? | Không (ghi rõ trong đề: mật khẩu dạng rõ; SSL là Chương 5) |

Mã phản hồi bắt chước kiểu `100 OK / 2xx / 999` của giao thức chat trong §4.3:

| Mã | Ý nghĩa |
|---|---|
| `100 OK [...]` | thành công |
| `110 FLIGHTS <k>` + k dòng, `111 RETURN <m>` + m dòng | kết quả nhiều dòng: **đếm trước** để client biết khi nào hết (cùng ý tưởng `OUTPUT <n>` của telnet) |
| `120 FILE <n>` + đúng n byte | nội dung vé để in |
| `200 USERNAME IN USE`, `201 INVALID`, `202 NOT FOUND`, `203 DENIED`, `204 LOGIN FIRST`, `205 NO SEATS`, `206 PAYMENT FAILED`, `207 ALREADY LOGGED IN`, `208 EXPIRED` | lỗi phía client |
| `300 TICKET <mã>`, `301 NOTIFY <loại> <chuyến> ...` | server **chủ động** gửi; có thể xen giữa các phản hồi |
| `500 FULL` | đủ N client, đóng kết nối |
| `999 UNKNOWN ERROR` | lệnh lạ / sai cú pháp |

Dữ liệu chuyến bay `flights.txt`, mỗi dòng một chuyến (đọc bằng `fgets` + `sscanf`, lab07):

```
VN213 VN HAN SGN 2026-12-20 06:00 08:10 1250000 120 3500000 20
VJ123 VJ HAN SGN 2026-12-20 23:30 01:35  890000 180       0  0
```

`<mã> <hãng> <đi> <đến> <ngày> <giờ đi> <giờ đến> <giá ECO> <ghế ECO> <giá BUS> <ghế BUS>`.
Giờ đến nhỏ hơn giờ đi nghĩa là hạ cánh sang ngày hôm sau (thời gian bay vẫn tính đúng).
So ngày bằng `strcmp` vì dạng `YYYY-MM-DD`.

## 3. Danh sách bài

Cột "Test" là số test dự kiến; bài khởi động luôn ít test hơn bài đích.

### A. Nền tảng giao thức (Chương 4)

**1. `fly-parse` — Kiểm tra cú pháp lệnh FLY** · stdio · easy · ch4 · ~20 test
- Đọc từng dòng lệnh từ stdin, in mã phản hồi cú pháp: `100 OK` hoặc `201 INVALID` / `999 UNKNOWN ERROR`.
  Không có mạng, không có trạng thái.
- Lệnh kiểm tra: `REGISTER/LOGIN <user> <pass>`, `SEARCH <đi> <đến> <ngày> <số khách> <ECO|BUS> [ngày về]`.
  Luật: user `[a-z0-9]{1,32}` (giống NICKNAME §4.3), mã sân bay 3 chữ hoa, ngày `YYYY-MM-DD` là
  **ngày có thật** (30/02 sai, năm nhuận đúng), ngày về không trước ngày đi, số khách 1–9,
  đúng số thành phần, đúng một dấu cách.
- Kỹ năng đơn lẻ: **tách và kiểm tra trường của một thông điệp text** (`strtok_r`, `sscanf`, `strcmp`,
  `isdigit/isupper`, lab09).
- Là khởi động của: fly-auth, fly-search.

**2. `flight-filter` — Lọc chuyến bay từ tệp** · stdio · easy · ch4 · ~20 test
- `./filter flights.txt`, stdin mỗi dòng một truy vấn `<đi> <đến> <ngày> <số khách> <hạng>`, in các chuyến
  còn đủ ghế hạng đó theo thứ tự trong tệp, kèm giá × số khách.
- Kỹ năng đơn lẻ: **nạp tệp dữ liệu vào mảng struct và lọc** (`fopen/fgets/sscanf`, lab07; mảng động lab03).
- Là khởi động của: fly-search, fly-compare.

**3. `chat-proto` — Chat server theo giao thức §4.3 (Bài tập 4.1)** · server · medium · ch4 · ~25 test
- Đúng code mẫu tuần này `4-Chap4/pthread_chatroom.c` mở rộng thành phần giao thức trong bài giảng:
  `JOIN <nick>` (`100 OK` / `200 NICKNAME IN USE` / `201 INVALID NICK NAME`), `MSG <text>` (phát cho mọi
  người khác dạng `[nick]: text`), `PMSG <nick> <text>` (gửi riêng, `202 UNKNOWN NICKNAME`), `QUIT`, lệnh lạ
  `999 UNKNOWN ERROR`. Bỏ OP/KICK/TOPIC để giữ bài dễ hơn bài đích.
- Kỹ năng đơn lẻ: **tìm đúng một client theo tên rồi gửi riêng** cho nó (duyệt danh sách liên kết
  dưới mutex như `get_nickname`). Phát cho mọi người đã có ở thread-chat nên không chấm nặng phần đó.
- Bẫy được nêu trong "Ràng buộc": code mẫu gọi `recv` một lần rồi coi là một lệnh, và truyền
  `&client_socket` cho luồng (đua dữ liệu). Bài yêu cầu ghép dòng và truyền fd đúng cách.
- Là khởi động của: fly-notify.

### B. Mảnh của BTL

**4. `fly-log` — Server ghi log mọi message** · server · easy · ch4 · ~20 test
- `./server <cổng> <tệp log>`. Giao thức tối thiểu: `PING` → `100 OK PONG`, còn lại `999 UNKNOWN ERROR`
  (để tập trung vào log). Phục vụ nhiều client bằng `select` hoặc pthread.
- Mỗi sự kiện ghi đúng một dòng, theo thứ tự xảy ra, **flush ngay**:
  ```
  [2026-11-26 14:03:05] CONNECT 127.0.0.1:53122
  [2026-11-26 14:03:05] RECV 127.0.0.1:53122 PING
  [2026-11-26 14:03:05] SEND 127.0.0.1:53122 100 OK PONG
  [2026-11-26 14:03:06] DISCONNECT 127.0.0.1:53122
  ```
- Kỹ năng: lấy địa chỉ client từ `accept` (`inet_ntoa`, `ntohs` như `udp_receiver.c`), timestamp bằng
  `time` + `localtime` + `strftime`, `fprintf` + `fflush`, log theo **dòng** chứ không theo lần `recv`.
  Bộ chấm kiểm tra định dạng thời gian và lệch không quá 2 giây so với giờ thật.
- Khác `tcp-greeting-log` (ghi byte thô của một client) ở chỗ ghi cả chiều gửi, theo dòng, nhiều client.

**5. `fly-auth` — Đăng ký, đăng nhập, tối đa N client** ⭐ · server · medium · ch4 · ~30 test
- `./server <cổng> <N> accounts.txt`. Lệnh `REGISTER`, `LOGIN`, `LOGOUT`, `WHOAMI`, `QUIT`.
- Tài khoản mới được **ghi nối** vào `accounts.txt` ngay; bộ chấm khởi động lại server và đăng nhập lại.
- Một tài khoản chỉ đăng nhập ở một kết nối tại một thời điểm (`207 ALREADY LOGGED IN`); kết nối đóng thì
  tự đăng xuất. Hai client `REGISTER` cùng tên đồng thời: đúng một người thắng.
- Đủ N client → `500 FULL` rồi đóng (đúng dạng đề giữa kỳ).
- Khởi động: fly-parse. Tham khảo cách đọc tệp tài khoản của telnet-select.

**6. `fly-search` — Tìm chuyến bay qua mạng** · server · medium · ch4 · ~30 test
- `./server <cổng> flights.txt`. `SEARCH <đi> <đến> <ngày> <khách> <hạng> [ngày về]`
  → `110 FLIGHTS k` + k dòng `<mã> <hãng> <giờ đi> <giờ đến> <tổng giá>`; có ngày về thì thêm
  `111 RETURN m` + m dòng cho chiều ngược lại. Không cần đăng nhập.
- Kỹ năng mới so với flight-filter: **phản hồi nhiều dòng có đếm trước** trên TCP, nhiều truy vấn dính nhau.
- Khởi động: fly-parse, flight-filter.

**7. `fly-compare` — So sánh giá và thời gian bay** · stdio · medium · ch4 · ~25 test
- Đọc `flights.txt`, mỗi truy vấn: `COMPARE <đi> <đến> <ngày> <khách> <hạng> PRICE|DURATION|DEPART`
  → danh sách sắp xếp (hòa thì theo mã chuyến); `BEST <đi> <đến> <ngày> <khách> <hạng>` → mỗi hãng một dòng:
  chuyến rẻ nhất và chuyến bay nhanh nhất của hãng đó.
- Kỹ năng: tính thời gian bay từ `HH:MM` (kể cả qua nửa đêm), sắp xếp bằng `qsort` với hàm so sánh
  có tiêu chí phụ (con trỏ hàm, lab05), nhóm theo hãng.
- Để stdio vì phần mạng giống hệt fly-search; capstone chỉ cần gắn thêm lệnh.
- Khởi động: flight-filter.

**8. `fly-book` — Đặt vé và thanh toán** ⭐ · server · hard · ch3 · ~35 test
- `./server <cổng> <N> <T giây giữ chỗ> flights.txt accounts.txt wallets.txt`.
  `BOOK <chuyến> <hạng> <khách>` → `100 OK HOLD <PNR> <số tiền> <hạn giữ HH:MM:SS>` (giữ ghế ngay) hoặc
  `205 NO SEATS`; `PAY <PNR> CARD <16 số> <MM/YY> <CVV>` (Luhn đúng, thẻ chưa hết hạn) hoặc
  `PAY <PNR> WALLET` (trừ số dư); `RELEASE <PNR>` trả ghế khi chưa thanh toán.
- Chỗ giữ chưa thanh toán **hết hạn sau T giây** thì ghế tự trả lại, kể cả khi không client nào gửi lệnh
  (dùng timeout của `select`, hoặc một luồng dọn dẹp nếu làm đa luồng). `PAY` một PNR đã hết hạn → `208 EXPIRED`.
- PNR là 6 ký tự ngẫu nhiên `A–Z0–9`, không trùng với PNR đang có.
- Trọng tâm thi giữa kỳ: **trạng thái dùng chung + đồng thời**: 50 client cùng tranh 3 ghế cuối, không được
  bán quá; giống mock-booking-tcp nhưng có số lượng và tiền.
- Khởi động: fly-auth, fly-search (đã có), kv-max-n (đã có).

**9. `fly-eticket` — Phát hành vé điện tử** · server · medium · ch4 · ~25 test
- `./server <cổng> <ip SMTP> <cổng SMTP> accounts.txt`. Bài tự đứng (không bắt làm lại fly-book): lệnh
  `ISSUE <chuyến> <hạng> <tên hành khách>` của người đã `LOGIN` mô phỏng "vừa thanh toán xong". Server:
  1. sinh số vé 13 chữ số theo kiểu vé thật (3 số mã hãng + 10 số, không trùng, dưới mutex) và lưu vào
     `tickets.txt` để khởi động lại không cấp trùng;
  2. **email thật**: mở kết nối TCP tới máy chủ SMTP và gửi `HELO`, `MAIL FROM`, `RCPT TO`, `DATA`
     (thư có `Subject`, `Date` theo giờ hiện tại, nội dung vé), `.`, `QUIT`, kiểm tra mã trả lời
     `220/250/354/221` từng bước. Đề cho sẵn đủ các lệnh SMTP cần dùng. Bộ chấm đóng vai máy chủ SMTP;
     làm BTL thật thì trỏ tới một SMTP server cục bộ hoặc của nhà cung cấp mail.
     Gửi mail lỗi thì vé vẫn phát hành, server trả `100 OK <số vé> MAIL_FAILED`;
  3. lưu bản sao thư vào `outbox/<user>/<số vé>.eml`;
  4. **tin nhắn** = đẩy `300 TICKET <số vé>` tới **mọi kết nối khác** đang đăng nhập cùng tài khoản.
- Kỹ năng: server vừa là server (với client) vừa là **client** (với SMTP), hội thoại lệnh–mã trả lời
  kiểu POP3 §4.2.3, tạo mã duy nhất, đẩy thông điệp chủ động.

**10. `fly-manage` — Quản lý vé đã đặt** · server · hard · ch4 · ~35 test
- Dữ liệu nạp sẵn `tickets.txt`, `wallets.txt`. Lệnh: `MYTICKETS` (`110`-kiểu nhiều dòng), `VIEW <mã>`,
  `CANCEL <mã>` (hoàn vào ví theo thời gian còn tới giờ bay: trên 72 giờ hoàn 90%, 24–72 giờ hoàn 70%,
  dưới 24 giờ hoàn 30%, đã bay thì `203 DENIED`; tính bằng `mktime` + `time`), `CHANGE <mã> <chuyến mới>`
  (cùng chặng, còn ghế, chỉ đổi khi còn trên 3 giờ; phí đổi cố định + chênh lệch giá trừ ví hoặc hoàn ví),
  `PRINT <mã>` → `120 FILE <n>` + n byte nội dung vé theo mẫu (có giờ in theo `strftime`).
- Bộ chấm sinh `flights.txt` với giờ bay **tính từ lúc chạy test** (+2 giờ, +30 giờ, +5 ngày…) để kiểm tra
  đủ các mức hoàn tiền.
- Không được thao tác vé của người khác (`203 DENIED`), vé đã hủy chỉ còn `VIEW`.
- Kỹ năng: máy trạng thái của vé, tính tiền bằng số nguyên, gửi nội dung có độ dài tiền tố.

**11. `fly-print-client` — Client in vé ra tệp** · client · medium · ch4 · ~20 test
- `./client <ip> <cổng> <user> <pass> <mã vé> <tệp ra>`: `LOGIN`, `PRINT`, nhận `120 FILE n` rồi **đúng n byte**
  (bị cắt nhiều mảnh, có byte lạ) ghi vào tệp bằng `fwrite`; gặp `202`/`203` thì in mã lỗi và không tạo tệp.
  Bộ chấm đóng vai server.
- Kỹ năng: phía **nhận** của độ dài tiền tố rồi ghi tệp (length-prefix hiện có là phía server).

**12. `fly-notify` — Thông báo chuyến bay** · server · hard · ch4 · ~35 test
- Người dùng `LOGIN` như thường. Admin `ADMIN <khóa>` rồi gửi `DELAY <chuyến> <phút>`,
  `RESCHEDULE <chuyến> <ngày> <giờ đi> <giờ đến>`, `CANCELFLIGHT <chuyến>`.
- Server đẩy `301 NOTIFY DELAY VN213 45` … tới **mọi kết nối** của mọi người có vé chuyến đó.
  Người đang offline: thông báo xếp hàng, giao ngay sau `100 OK` của lần `LOGIN` tiếp theo, đúng thứ tự.
- Kỹ năng: server chủ động (§4.3), phân quyền theo phiên (giống `OP/KICK` "chủ phòng" §4.3), hàng đợi theo người.
- Khởi động: chat-proto (gửi riêng theo tên).

**13. `fly-client` — Giao diện console** · client · hard · ch4 · ~25 test
- Client có menu số (`1. Đăng nhập 2. Tìm chuyến 3. Đặt vé 4. Vé của tôi 5. Thoát`), người dùng
  **không gõ lệnh giao thức** (đúng yêu cầu "cung cấp giao diện cơ bản" ở §4.2.2/§4.2.3). Chuyển lựa chọn
  thành lệnh FLY, in kết quả theo định dạng quy định; `301 NOTIFY` đến lúc nào cũng in ngay
  (`select` trên stdin + socket như `select_client.c`).
- Gợi ý bảng điều phối lệnh bằng con trỏ hàm (lab05). Bộ chấm đóng vai server và người gõ phím.
- Khởi động: chat-client (đã có), fly-print-client.

### C. Nâng cao và ôn thi

**14. `fly-web` — Giao diện web tìm chuyến** · server · hard · ch4 · ~30 test
- Theo đúng `4-Chap4/http_server.c`: mỗi kết nối một luồng, đọc tới `\r\n\r\n`, `sscanf` lấy method/path,
  ghép chuỗi bằng `realloc` kiểu `AppendStr`, `Content-Length` đúng.
  `GET /` → trang HTML có form; `GET /search?from=HAN&to=SGN&date=...&pax=2&class=ECO` → bảng HTML kết quả;
  giải mã `%20` và `+`; tham số thiếu → `400`; đường dẫn khác → `404`.
- Bộ chấm phân tích HTML theo vài thẻ cố định (`<tr>` mỗi chuyến), không so cả trang.
- Khởi động: looping-server (đã có).

**15. `fly-status-udp` — Tra cứu trạng thái chuyến qua UDP** ⭐ · server · medium · ch2 · ~25 test
- `udp_receiver.c` mở rộng: datagram `STATUS <chuyến> <ngày>` → `ON_TIME` / `DELAYED <phút>` / `CANCELLED` /
  `NOT_FOUND`; datagram admin `SET <khóa> <chuyến> <ngày> <trạng thái>` cập nhật. Mỗi datagram là một lệnh,
  trả lời đúng địa chỉ gửi (`recvfrom`/`sendto`).
- Luyện UDP cho giữa kỳ (đề có thể là UDP), đồng thời là tính năng nâng cao "tra cứu nhanh không cần đăng nhập".

**16. `mock-flight-tcp` — Thi thử 3: Đặt vé máy bay tối đa N client** ⭐ · server · hard · exam 90 phút · test ẩn
- Rút gọn từ các bài trên cho vừa 90 phút: `LOGIN` (tài khoản từ tệp, không REGISTER), `SEARCH` không có ngày về,
  `BOOK` trả tiền ngay bằng ví, `MYTICKETS`, `CANCEL`; N client, `FULL`.
- Không gợi ý, `hide_details: true` như hai đề thi thử hiện có.

## 4. Kiểm tra tiêu chí bài khởi động

| Bài đích (test) | Kỹ năng của bài đích | Khởi động và kỹ năng nó tách ra |
|---|---|---|
| fly-auth (~30) | tách/kiểm tra lệnh · tệp tài khoản · trạng thái phiên · N client | **fly-parse** (~20): chỉ tách/kiểm tra lệnh. N client đã có echo-max-n |
| fly-search (~30) | kiểm tra lệnh · nạp tệp + lọc · phản hồi nhiều dòng | **fly-parse**, **flight-filter** (~20): mỗi bài một kỹ năng, không chồng nhau |
| fly-compare (~25) | nạp tệp + lọc · tính giờ bay · sắp xếp · nhóm | **flight-filter** |
| fly-notify (~35) | tìm client theo tên/người dùng · phân quyền · hàng đợi offline | **chat-proto** (~25): chỉ phần gửi riêng theo tên |
| fly-client (~25) | select stdin + socket · nhận nhiều dòng/độ dài tiền tố · menu | chat-client (có sẵn), **fly-print-client** (~20) |

Không có bài nào là hợp của hai bài khác. fly-eticket, fly-manage, fly-log đứng một mình (kỹ năng
đã có bài nền: tcp-greeting-log, length-prefix, telnet-select).

## 5. Hàm được dùng

**Phần mạng: chỉ dùng những gì có trong code mẫu và slide.**

| Hàm/kỹ thuật mạng dùng trong lời giải | Có trong |
|---|---|
| `socket/bind/listen/accept/connect/send/recv/close`, `setsockopt SO_REUSEADDR` | `tcp_server.c`, `tcp_client.c`, `html.c` |
| `inet_addr`, `inet_ntoa`, `htons/ntohs`, `sendto`, `recvfrom` | `udp_receiver.c`, `music_server.c` |
| `select`, `FD_SET/FD_ISSET`, timeout `struct timeval` | `select_server.c`, `select_client.c` |
| `pthread_create/detach`, `pthread_mutex_lock/unlock`, danh sách liên kết client | `4-Chap4/pthread_chatroom.c` |
| `fork`, `waitpid`, `SIGCHLD` | `forking_server.c` |
| đọc HTTP request tới `\r\n\r\n`, `Content-Length`, ghép chuỗi `AppendStr` | `4-Chap4/http_server.c` |

### 5.1. Hàm mạng ngoài code mẫu: dùng có giúp BTL tốt hơn không?

| Hàm | Làm gì | Có giúp BTL tốt hơn? | Kết luận |
|---|---|---|---|
| `MSG_NOSIGNAL` (cờ của `send`), hoặc `signal(SIGPIPE, SIG_IGN)` | `send` vào kết nối client đã chết thì trả `-1` (lỗi `EPIPE`) thay vì hệ điều hành gửi tín hiệu `SIGPIPE` **giết cả server** | **Có, rõ nhất.** BTL đẩy thông báo/vé điện tử cho client bất cứ lúc nào, nên rất dễ đẩy trúng một client vừa rớt mạng. Không có nó, một client rớt mạng làm sập server của mọi người, mất luôn ghế đang giữ | **Nên dùng.** Đưa vào thẻ kiến thức và gợi ý của fly-book, fly-eticket, fly-notify. `signal()` đã có trong code mẫu (ex4–ex6), chỉ `SIG_IGN`/`SIGPIPE` là mới |
| `inet_pton` / `inet_ntop` | Đổi địa chỉ chuỗi ↔ nhị phân, báo lỗi rõ ràng, hỗ trợ IPv6 | **Ít.** Có ích khi kiểm tra tham số `<ip SMTP>` / `<ip server>` của client: `inet_addr` coi `255.255.255.255` là lỗi và không có IPv6. BTL chạy IPv4 nội bộ nên khác biệt nhỏ | **Tùy chọn.** Giải thích trong thẻ kiến thức; không test nào cần |
| `poll` | Giống `select` nhưng dùng mảng `struct pollfd`: không phải dựng lại tập fd mỗi vòng, không bị giới hạn `FD_SETSIZE` = 1024 | **Ít.** Code gọn hơn khi nhiều client, nhưng BTL vài chục client thì `select` vẫn đủ. Không có tính năng nào cần `poll` | **Tùy chọn.** Giải thích, so sánh với `select` |
| `fcntl(fd, F_SETFL, O_NONBLOCK)` | Đặt socket không chặn | **Không thêm gì** so với `ioctl(fd, FIONBIO, &on)` đã có trong `non_blocking_server.c`, chỉ là cách viết chuẩn POSIX hơn | **Tùy chọn**, chỉ nhắc tên là cách viết tương đương |
| `shutdown(fd, SHUT_WR)` | Đóng **một chiều**: báo "tôi gửi xong" nhưng vẫn nhận tiếp | **Hầu như không.** Giao thức FLY theo dòng, có `QUIT`, có đếm trước số dòng/byte, nên không cần đánh dấu hết dữ liệu bằng đóng kết nối | **Tùy chọn**, chỉ giải thích; không gợi ý trong bài nào |
| `errno` + `EINTR`/`EAGAIN`/`EPIPE` | Biết **vì sao** một lời gọi thất bại | **Có, nhỏ.** Log ghi được lý do lỗi (`strerror(errno)`), phân biệt "client đóng" với "lỗi thật" | **Nên dùng trong log**, đi kèm `MSG_NOSIGNAL` |

Quy ước khi viết bài:
- Lời giải chuẩn (`solution.c`) chỉ dùng code mẫu, để chắc chắn làm được bằng kiến thức trên lớp.
- Hàm tùy chọn được ghi trong đề ở mục **"Được phép dùng thêm"**, kèm liên kết thẻ kiến thức.
- **Test về client chết khi server đang đẩy dữ liệu** chỉ có ở fly-notify và fly-eticket (đề thi thử
  mock-flight-tcp không có, cho đúng phạm vi giữa kỳ).
  Đề ghi rõ yêu cầu "server không được sập". Lời giải chuẩn dùng `signal(SIGPIPE, SIG_IGN)` (chỉ thêm một
  hằng so với code mẫu). Các bài cũ vẫn bỏ loại test này như trước.
- Các hàm còn lại không có test nào phụ thuộc: dùng hay không đều qua.

**Phần C/thư viện chung: dùng thoải mái**, ví dụ `time/localtime/strftime/mktime/difftime`, `rand/srand`,
`qsort`, `ctype.h`, `strtol/strtoul`, `mkdir/stat/opendir`, `snprintf`, `fopen/fgets/fprintf/fflush`.

## 6. Study plan

**Plan mới `btl-ve-may-bay`** — "BTL: Đặt vé máy bay online", order 7, ~10 ngày, các section theo đúng
barem (ghi điểm ở `intro`):

1. Thiết kế giao thức (§4.3) — fly-parse, chat-proto
2. Log server (1đ) — fly-log
3. Tài khoản (2đ) — fly-auth
4. Tìm kiếm và so sánh (2đ + 2đ) — flight-filter, fly-search, fly-compare
5. Đặt vé, thanh toán, vé điện tử (3đ + 2đ) — fly-book, fly-eticket
6. Quản lý vé (3đ) — fly-manage, fly-print-client
7. Thông báo (3đ) — fly-notify
8. Giao diện (3đ) — fly-client, fly-web
9. Nâng cao và thi thử — fly-status-udp, mock-flight-tcp

**Thêm vào plan cũ** (đề xuất):

| Plan | Thêm |
|---|---|
| giua-ky | fly-auth vào "Tối đa N client & thi thử"; fly-status-udp vào "UDP"; mock-flight-tcp vào cuối |
| kien-truc-server | chat-proto vào "Chat: select, pthread" |
| tcp-luong-byte-giao-thuc | fly-parse vào "Ghép dòng", fly-print-client vào "Độ dài tiền tố" |
| client-toan-tap | fly-print-client, fly-client |
| thu-thach-hard | fly-book, fly-notify, mock-flight-tcp |

## 7. Kiến thức, gợi ý, quiz

- Thẻ kiến thức mới: `knowledge/protocol-design.md` (6 câu hỏi §4.3, mã phản hồi, thông điệp chủ động,
  phản hồi nhiều dòng đếm trước, HTTP request/response §4.2.1) và `knowledge/http-server.md`
  (đọc hiểu `http_server.c`: đọc tới `\r\n\r\n`, `Content-Length`, `AppendStr`, POST body).
- Thẻ kiến thức mới `knowledge/ngoai-code-mau.md` — "Hàm mạng ngoài code mẫu (tùy chọn)": mỗi hàm ở mục 5.1
  có chữ ký, ví dụ ngắn, so sánh với cách trong code mẫu và khi nào nên dùng. Nhãn rõ "không bắt buộc, không
  có trong đề thi giữa kỳ". `SIGPIPE`/`MSG_NOSIGNAL` đặt đầu tiên vì là cái đáng dùng nhất.
- `hints.yaml`: 3 bậc cho mỗi bài trừ mock-flight-tcp.
- `quiz.yaml` / `flashcards.yaml`: thêm ~15 câu §4.1–4.3 (HTTP stateless, cấu trúc request/response,
  nhóm mã 1xx–5xx, FTP kênh điều khiển/dữ liệu, chủ động/bị động, 3 trạng thái POP3, giao thức chat).
- `bugs.yaml`: lỗi trong code mẫu đáng học (`recv` một lần = một lệnh; `&client_socket` truyền cho luồng;
  `sscanf("%s")` vào mảng cố định; `send` header và body tách rời vẫn đúng vì TCP là luồng byte).

## 8. Kiểm thử (theo TEST-DESIGN.md)

Mỗi bài có đủ nhóm sample/basic/edge/stream/robust/concurrency/stress, solution.c + wrong/*.c + mutants.yaml,
selftest xanh. Các test "nguy hiểm" riêng của bộ này:

- Dòng lệnh bị cắt từng byte / hàng trăm lệnh dính nhau (mọi bài server).
- Tệp log phải có dòng `RECV` **trước** khi client nhận phản hồi (bộ chấm đọc log ngay sau khi nhận).
- Đặt vé đồng thời: 50 client tranh ghế cuối; tổng ghế bán ≤ ghế có.
- Khởi động lại server: tài khoản, bộ đếm mã vé, ví còn nguyên.
- Thông báo đẩy xen giữa phản hồi `110 FLIGHTS k`: client phải in đúng cả hai.
- Chuyến qua nửa đêm; giá × số khách vượt `int` 32 bit? (giá tối đa 10^8 × 9 < 2^31 → không, ghi rõ ràng buộc).
- Thời gian: giữ chỗ hết hạn khi **không có lệnh nào** gửi tới (bộ chấm chờ T+1 giây rồi cho client khác
  đặt đúng ghế đó); thẻ hết hạn tháng trước / còn hạn tháng này; hoàn tiền ở sát mốc 24 giờ và 72 giờ.
- SMTP: máy chủ giả trả lời nhiều dòng `250-...`, trả `550` cho `RCPT TO`, đóng kết nối giữa chừng,
  hoặc không chạy (connect thất bại) → server vẫn phục vụ client bình thường.
- PNR ngẫu nhiên: 2000 lần đặt không có PNR trùng, đúng định dạng.
- Giới hạn 256 file descriptor như các bài cũ.

## 9. Thứ tự làm

- **Đợt 1 (trước 30/11, có ích cho thi 15/12):** fly-parse, fly-auth, fly-book, fly-status-udp,
  mock-flight-tcp, flight-filter, fly-search.
- **Đợt 2 (sau thi):** chat-proto, fly-log, fly-compare, fly-eticket, fly-manage, fly-print-client,
  fly-notify, fly-client, fly-web, plan `btl-ve-may-bay`, thẻ kiến thức.

## 10. Cần bạn quyết

1. Dùng chung giao thức FLY và mã phản hồi kiểu §4.3 cho mọi bài — đồng ý?
2. Email gửi thật qua SMTP (giao thức không có trong slide, đề cho sẵn các lệnh), tin nhắn = đẩy
   `300 TICKET` qua socket, thanh toán mô phỏng (Luhn + hạn thẻ + CVV, ví) — được chứ? Nếu SMTP vượt
   phạm vi môn thì lùi về ghi thư vào `outbox/`.
3. Giao diện: chấm **console menu** (fly-client) + **web** (fly-web). GUI thật (GTK/Qt) ngoài code mẫu nên không làm.
4. Thứ tự hai đợt ở mục 9, và danh sách thêm vào plan `giua-ky` ở mục 6.
5. Cho fly-notify và fly-eticket có test "client chết khi server đang đẩy" (bắt phải xử lý `SIGPIPE`) như
   mục 5.1 — đồng ý? Nếu không, các bài này cũng bỏ loại test đó và `SIGPIPE` chỉ còn là gợi ý.
6. 16 bài có nhiều quá không? Nếu cần cắt, đề xuất bỏ fly-eticket (gộp vào fly-book) và fly-log
   (gộp yêu cầu log vào fly-auth) → còn 14.

---

## 11. Ghi chú triển khai (chỗ bài thật khác bản thiết kế)

Cả 16 bài nằm trong `problems/`, `selftest` xanh (solution AC, mọi `wrong/*.c` và mutant đều bị giết), có plan `plans/btl-ve-may-bay.yaml`, thẻ kiến thức
`knowledge/protocol-design.md`, `ngoai-code-mau.md`, `http-server.md`, gợi ý 3 bậc cho mọi bài (trừ `mock-flight-tcp`), quiz và flashcard.

| Bài | Chênh lệch so với thiết kế |
|---|---|
| `fly-book` | "Hạn giữ chỗ" in ra dạng `HH:MM:SS` giờ địa phương (đúng thiết kế); thêm mã `208 EXPIRED`, `209 ALREADY PAID`, lệnh `SEATS`, `BALANCE`; mô hình thời gian chỉ xét ở thời điểm lệnh đến, bộ chấm chờ thật T+1.5 giây (T = 2) |
| `fly-eticket` | Thêm tệp `accounts.txt` có cột email, `tickets.txt`; SMTP giả ở `127.0.0.1:2525` kiểm tra từng byte; thêm timeout 2 giây cho mỗi phản hồi SMTP |
| `fly-manage` | Giờ hệ thống truyền qua tham số `<ngày> <giờ>` để test tất định (BTL thật thay bằng `time(NULL)`); thêm mã `210 TOO LATE`, `211 DIFFERENT ROUTE`; có 22+ giá trị giờ kiểm tra biên 72h / 24h / 3h / ±1 phút và năm nhuận |
| `fly-notify` | Thêm `STATUS`, `ADMIN <khóa>`; hàng đợi cho tài khoản offline; test bắt buộc xử lý `SIGPIPE` (đã duyệt) |
| `fly-client` | `fly-print-client` là bài khởi động; `fly-client` bắt buộc `select`, nhận `301 NOTIFY` bất kỳ lúc nào |
| `fly-web` | Thêm `GET /flight/<mã>`, `POST /search` đọc đủ `Content-Length`; chuỗi HTML bắt buộc được liệt kê trong đề |
| `fly-compare` | Tập dữ liệu có 11 chuyến hòa khóa để kiểm tra khóa phụ của `qsort` |
| `mock-flight-tcp` | Dùng từ vựng đơn giản kiểu `mock-booking-tcp` (`WELCOME`, `TICKET T0001`, `NO_MONEY`...), không dùng mã `1xx/2xx` |

Lưu ý khi viết thêm bài: tránh `python - <<EOF` có `\n` hay `\r` trong chuỗi khi sửa tệp qua Bash (bị đổi thành ký tự xuống dòng thật); dùng công cụ Edit/Write.
