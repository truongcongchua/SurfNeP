# Chat server theo giao thức §4.3

Bài tập 4.1 của bài giảng: lập trình **chat server** theo giao thức mô tả ở §4.3 (phiên bản rút gọn: không có `OP`,
`KICK`, `TOPIC`). Code mẫu tuần này là `4-Chap4/pthread_chatroom.c` (đa luồng, danh sách client có `nickname`). Bài này
là khởi động cho phần **thông báo** của bài tập lớn: cần tìm đúng **một** client theo tên rồi gửi riêng cho nó.

Viết `./chat_server <cổng>` phục vụ nhiều client cùng lúc (ít nhất 30). Dùng `select` hoặc `pthread` (nhớ mutex khi
duyệt danh sách client).

## Giao thức

Mỗi lệnh là một dòng `\n` (bỏ **một** `\r` cuối dòng nếu có, tối đa 1000 byte). Tên lệnh viết hoa, sau tên lệnh là **đúng một
dấu cách** rồi tham số. Server không chào khi client kết nối; client chưa `JOIN` là **chưa vào phòng**.

| Lệnh | Điều kiện | Phản hồi cho người gửi |
|---|---|---|
| `JOIN <nick>` | `nick` gồm 1–32 ký tự `a-z0-9` | `100 OK`; `201 INVALID NICK NAME` nếu sai quy cách; `200 NICKNAME IN USE` nếu đã có người đang dùng; `203 DENIED` nếu client này đã `JOIN` rồi |
| `MSG <text>` | đã `JOIN`, `text` khác rỗng (có thể chứa dấu cách) | `100 OK`; chưa `JOIN` → `203 DENIED` |
| `PMSG <nick> <text>` | đã `JOIN`, `text` khác rỗng | `100 OK`; `202 UNKNOWN NICKNAME` nếu không có **người khác** đã `JOIN` với tên đó (gửi cho chính mình cũng là `202`); chưa `JOIN` → `203 DENIED` |
| `QUIT` | | `100 OK` rồi đóng kết nối |
| mọi thứ khác (lệnh lạ, `MSG` / `PMSG` thiếu thành phần, dòng trống) | | `999 UNKNOWN ERROR` |

Thứ tự kiểm tra: `JOIN` — client đã `JOIN` rồi (`203`) → quy cách tên (`201`) → tên đã dùng (`200`); `MSG`/`PMSG` — tên lệnh và cú pháp (`999`) → đã `JOIN` chưa (`203`) → người nhận (`202`).

Lệnh tách theo **dấu cách đầu tiên**: phần trước là tên lệnh, phần sau là tham số *nguyên văn* (`JOIN a b` có tên `a b` nên `201`; `JOIN ` với tên rỗng cũng `201`; `JOIN` không có dấu cách là `999`). `PMSG <nick> <text>` tách tiếp ở dấu cách thứ hai.

**Server chủ động gửi** (không cần client hỏi):
- `MSG <text>` của `an` → mọi client **khác** đã `JOIN` nhận dòng `[an]: <text>`. Không gửi lại cho người gửi, không gửi
  cho client chưa `JOIN`.
- `PMSG <nick> <text>` của `an` → **chỉ** client tên `<nick>` nhận dòng `[an] (private): <text>`.
- Server gửi tin cho người nhận **trước khi** trả `100 OK` cho người gửi.
- Client rời đi (kể cả đột ngột) thì tên của nó được **giải phóng** để người khác dùng.

## Ví dụ

```
A: JOIN an            ← 100 OK
A: JOIN an            ← 203 DENIED
B: JOIN An            ← 201 INVALID NICK NAME
B: JOIN binh          ← 100 OK
C: JOIN an            ← 200 NICKNAME IN USE
A: MSG xin chao moi nguoi   ← 100 OK                 (B nhận: [an]: xin chao moi nguoi)
B: PMSG an chao ban   ← 100 OK                       (A nhận: [binh] (private): chao ban)
B: PMSG ai do hi      ← 202 UNKNOWN NICKNAME
C: MSG hi             ← 203 DENIED                   (C chưa JOIN)
A: QUIT               ← 100 OK
C: JOIN an            ← 100 OK                       (tên đã được giải phóng)
```

## Ràng buộc và bộ chấm kiểm tra
- `text` giữ nguyên mọi byte sau dấu cách đầu tiên (kể cả dấu cách thừa ở giữa và cuối, dấu nháy, ký tự lạ ≥ 0x80), tối đa 900 byte.
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng chục lệnh dính nhau trong một lần gửi.
- Client im lặng hoặc gửi dở lệnh **không** được làm chậm client khác.
- Client có thể mất kết nối đột ngột (RST) sau khi mọi phản hồi đã được đọc; bộ chấm chạy 300 lượt vào-ra với giới hạn 256 file
  descriptor.
- Lưu ý với code mẫu: `pthread_chatroom.c` gọi `recv` **một lần** rồi coi cả bộ đệm là một lệnh, và truyền `&client_socket` cho
  luồng. Cả hai đều là lỗi trong bài này (ghép dòng; truyền giá trị chứ không truyền địa chỉ biến của vòng `accept`).

## Kiến thức nền
§4.3 (chat server), `pthread_chatroom.c` (danh sách liên kết client, `get_nickname`), `chat-select` (ghép dòng và phát tin).
