# Tra cứu trạng thái chuyến bay qua UDP

Tính năng "tra cứu nhanh" của bài tập lớn đặt vé máy bay: khách **không cần đăng nhập** vẫn hỏi được một chuyến
đang đúng giờ, trễ hay bị hủy, qua một dịch vụ UDP rất nhẹ. Viết server UDP chạy bằng `./server <cổng> <khóa>`.

Khi khởi động, server nạp `flights.txt` (định dạng như bài *flight-filter*; chỉ cần cột **mã chuyến** và **ngày**).
Mỗi cặp `(mã chuyến, ngày)` có trong tệp bắt đầu ở trạng thái `ON_TIME`. Trạng thái được **dùng chung** cho mọi client
và chỉ nằm trong bộ nhớ.

## Giao thức

Mỗi **datagram** là đúng một lệnh (UDP giữ nguyên ranh giới thông điệp). Bỏ một `\n` rồi một `\r` ở cuối nếu có.
Các thành phần cách nhau bởi **đúng một dấu cách**. Server trả lời bằng **một** datagram gửi lại đúng địa chỉ đã gửi
lệnh, kết thúc bằng `\n`.

| Lệnh | Phản hồi |
|---|---|
| `STATUS <chuyến> <ngày>` | `ON_TIME`, `DELAYED <phút>`, `CANCELLED`, hoặc `NOT_FOUND` nếu cặp (chuyến, ngày) không có trong tệp |
| `SET <khóa> <chuyến> <ngày> ON_TIME` | đặt trạng thái; phản hồi `OK` |
| `SET <khóa> <chuyến> <ngày> CANCELLED` | như trên |
| `SET <khóa> <chuyến> <ngày> DELAYED <phút>` | như trên; `phút` là số nguyên thập phân từ 1 đến 1440, không dấu, không số 0 đứng đầu |
| `SET` đúng cú pháp nhưng `<khóa>` sai | `DENIED` |
| `SET` đúng khóa nhưng cặp (chuyến, ngày) không có | `NOT_FOUND` |
| mọi thứ khác (sai cú pháp, thiếu/thừa thành phần, trạng thái lạ, phút ngoài khoảng, datagram rỗng, dài hơn 1000 byte) | `ERROR` |

Thứ tự kiểm tra `SET`: **cú pháp** (cho ra `ERROR`) → **khóa** (`DENIED`) → **tồn tại** (`NOT_FOUND`). Tên lệnh và
trạng thái phân biệt hoa thường; khóa so sánh nguyên văn.

## Ví dụ (khóa `fly2026`)

```
→ STATUS VN213 2026-12-20            ← ON_TIME
→ SET fly2026 VN213 2026-12-20 DELAYED 45   ← OK
→ STATUS VN213 2026-12-20            ← DELAYED 45
→ SET sai VN213 2026-12-20 CANCELLED ← DENIED
→ STATUS VN213 2026-12-21            ← NOT_FOUND
→ SET fly2026 VN213 2026-12-20 DELAYED 0   ← ERROR
→ PING                               ← ERROR
```

## Ràng buộc và bộ chấm kiểm tra
- Hai chuyến khác ngày là hai cặp khác nhau; dữ liệu thật là `flights.txt` của bộ chấm (47 chuyến).
- Nhiều client (nhiều socket UDP) hỏi xen kẽ: thay đổi của một client phải được các client khác thấy ngay, và mỗi phản hồi
  chỉ về đúng nơi gửi lệnh.
- Client có thể gửi lệnh rồi đóng socket ngay, hoặc gửi datagram rỗng / rất dài (tới 65000 byte): server **không được
  sập** và vẫn phục vụ tiếp.
- Datagram không chứa byte `0x00`.

## Kiến thức nền
`recvfrom` / `sendto` (§2.4, `udp_receiver.c`, `music_server.c`): mỗi lần `recvfrom` nhận trọn một datagram và cho biết
địa chỉ người gửi, nên không cần ghép dòng như TCP; nhưng bộ đệm nhận phải đủ lớn và phải kiểm tra độ dài.
