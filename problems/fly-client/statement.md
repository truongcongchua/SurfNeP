# Client console có menu (giao diện BTL)

Phần "giao diện" (3 điểm) của bài tập lớn đặt vé máy bay. §4.2.2–4.2.3 yêu cầu client "cung cấp giao diện cơ bản (người dùng **không** trực
tiếp nhập các lệnh giao thức)". Bài này làm đúng việc đó cho giao thức FLY: một chương trình dòng lệnh có **menu số**, hỏi từng thông tin,
tự ghép thành lệnh gửi server và trình bày kết quả; đồng thời **nhận thông báo của server bất cứ lúc nào** (kể cả khi đang chờ bạn gõ phím), như
`select_client.c`.

Viết `./client <ip> <cổng>`. Bộ chấm đóng vai server (nói giao thức FLY) và đóng vai người dùng gõ vào `stdin`. **Bắt buộc dùng `select`** (không dùng `fork`,
`pthread`).

## Kết nối
Khi kết nối thành công server gửi dòng chào. Nếu dòng chào bắt đầu bằng `500` (đầy) thì in `Server day: <dòng chào>` rồi thoát mã **1**. Mọi dòng chào khác
(`100 OK WELCOME`) chỉ cần đọc bỏ. Không kết nối được: in `Khong ket noi duoc` rồi thoát mã 1.

## Menu và các chức năng

Hiển thị menu **ở đầu và sau mỗi chức năng** (mỗi dòng kết thúc `\n`, riêng `Chon: ` không có `\n`):
```
=== FLY ===
1. Dang nhap
2. Tim chuyen
3. Dat ve
4. Ve cua toi
5. Thoat
Chon: 
```
Người dùng gõ một số rồi Enter. Mỗi chức năng **hỏi lần lượt các dòng sau** (mỗi dòng gõ vào là một giá trị, nguyên văn đến hết dòng, bỏ `\r\n`), rồi gửi lệnh:

| Chọn | Hỏi lần lượt (nhãn in ra, không có `\n`) | Lệnh gửi server |
|---|---|---|
| `1` | `User: ` · `Pass: ` | `LOGIN <user> <pass>` |
| `2` | `Di: ` · `Den: ` · `Ngay: ` · `So khach: ` · `Hang (ECO/BUS): ` | `SEARCH <di> <den> <ngay> <khach> <hang>` |
| `3` | `Chuyen: ` · `Ngay: ` · `Hang (ECO/BUS): ` · `So khach: ` | `BOOK <chuyen> <ngay> <hang> <khach>` |
| `4` | (không hỏi gì) | `MYTICKETS` |
| `5` | (không hỏi gì) | `QUIT`; chờ phản hồi `100 OK`; thoát mã **0** |

Mọi giá trị được gửi **nguyên văn**, client không tự kiểm tra (server mới kiểm tra). Server luôn trả lời đúng **một** phản hồi cho mỗi lệnh; hiển thị như sau
(mỗi dòng in kết thúc `\n`):

| Phản hồi của server | Client in |
|---|---|
| `LOGIN`: `100 OK <user>` | `Xin chao <user>` |
| `SEARCH`: `110 FLIGHTS <k>` rồi `k` dòng `<mã> <hãng> <giờ đi> <giờ đến> <tổng tiền>` | `Co <k> chuyen:` rồi mỗi chuyến một dòng `<n>. <mã> <hãng> <giờ đi>-<giờ đến> <tổng tiền>` (n từ 1) |
| `BOOK`: `100 OK HOLD <PNR> <số tiền> <hạn>` | `Giu cho thanh cong. Ma: <PNR> So tien: <số tiền> Han: <hạn>`, rồi **hỏi thanh toán** (bên dưới) |
| `MYTICKETS`: `110 TICKETS <k>` rồi `k` dòng `<số vé> <chuyến> <ngày> <hạng> <hành khách> <giá> <trạng thái>` | `Ban co <k> ve:` rồi mỗi vé một dòng `<n>. <số vé> <chuyến> <ngày> <hạng> <trạng thái>` |
| bất kỳ phản hồi lỗi nào (dòng không bắt đầu bằng `100` hoặc `110`) | `Loi: <nguyên dòng server gửi>` |

**Hỏi thanh toán** (chỉ sau `BOOK` thành công): in `Thanh toan (1=Vi, 2=The, 0=Bo qua): ` rồi đọc một dòng:
- `1` → gửi `PAY <PNR> WALLET`;
- `2` → hỏi `So the: ` · `Het han (MM/YY): ` · `CVV: ` rồi gửi `PAY <PNR> CARD <số thẻ> <hết hạn> <cvv>`;
- `0` hoặc bất kỳ thứ gì khác → in `Chua thanh toan` và không gửi gì.
Phản hồi của `PAY`: `100 OK PAID <PNR>` → in `Da thanh toan <PNR>`; lỗi → `Loi: <nguyên dòng>`.

Lựa chọn menu không phải `1`–`5` (kể cả dòng trống): in `Lua chon khong hop le` và **không gửi gì** cho server.
`stdin` kết thúc (EOF) bất cứ lúc nào: gửi `QUIT` rồi thoát mã 0 (không cần đợi phản hồi). Server đóng kết nối bất ngờ: in `Mat ket noi` và thoát mã 1.

## Thông báo của server (chủ động gửi)

Bất cứ lúc nào server có thể gửi dòng `301 NOTIFY <nội dung>` (ví dụ `301 NOTIFY DELAY VN100 45`). Client phải in **ngay**:
```
[THONG BAO] DELAY VN100 45
```
kể cả khi: đang chờ bạn gõ lựa chọn menu; đang chờ một dòng trả lời câu hỏi (ví dụ giữa `User: ` và `Pass: `); hoặc đang chờ phản hồi của một lệnh
(thông báo nằm **xen giữa** lệnh và phản hồi, hay xen giữa các dòng của phản hồi nhiều dòng). Thông báo không làm mất hay đảo thứ tự các dòng đang gõ/đang nhận.

## Ví dụ

```
(server) 100 OK WELCOME
(client) === FLY ===  ...  Chon:            (người dùng gõ 1)
(client) User:                              (an)
(client) Pass:                              (1234)
(client → server) LOGIN an 1234
(server) 100 OK an
(client) Xin chao an
(client) === FLY === ...
(server, bất ngờ) 301 NOTIFY DELAY VN100 45
(client) [THONG BAO] DELAY VN100 45
```

## Ràng buộc và bộ chấm kiểm tra
- Phản hồi và thông báo của server có thể đến **từng byte**, hoặc nhiều dòng dính nhau (kể cả `110 FLIGHTS 2` + hai dòng + thông báo trong một lần gửi).
- Bộ chấm kiểm tra các dòng bạn in ra (có xuống dòng); không so cả menu và nhãn câu hỏi, nhưng các chuỗi `Xin chao`, `Co <k> chuyen:`, `Loi:`, `[THONG BAO]`...
  phải đúng như bảng.
- Bộ chấm viết `stdin` từng dòng một, chờ lệnh tương ứng đến server rồi mới viết tiếp; dùng `stdin` buffer của C (`fgets`) trộn với `select` là bẫy
  (dữ liệu đã nằm trong bộ đệm của `FILE` mà `select` không thấy): hãy đọc `stdin` bằng `read(0, ...)` rồi tự tách dòng.

## Kiến thức nền
`select_client.c` (§3.5): `fd_set` gồm `STDIN_FILENO` và socket. Phía mạng giữ bộ đệm dòng như `fly-print-client`. Gợi ý bảng điều phối lệnh bằng con trỏ hàm (lab05).
