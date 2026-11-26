# Tìm chuyến bay qua mạng

Mảnh "tìm kiếm chuyến bay" của bài tập lớn đặt vé máy bay, lần này **qua mạng**. Viết server TCP chạy bằng
`./server <cổng>`. Khi khởi động, server nạp `flights.txt` (thư mục hiện hành, định dạng như bài *flight-filter*) vào
bộ nhớ; sau đó trả lời các lệnh text của nhiều client cùng lúc. Chọn kỹ thuật tùy ý trong code mẫu (`select`,
`pthread`); `fork` cũng được vì dữ liệu chỉ đọc.

## Giao thức

Mỗi lệnh là **một dòng** kết thúc bằng `\n` (bỏ **một** `\r` cuối dòng nếu có), tối đa 1000 byte. Các thành phần
cách nhau bởi **đúng một dấu cách** (dấu cách thừa tạo thành phần rỗng và làm lệnh sai, như bài *fly-parse*).
Server không chào khi client kết nối, và mỗi lệnh có đúng một phản hồi (có thể nhiều dòng).

| Lệnh | Phản hồi |
|---|---|
| `SEARCH <đi> <đến> <ngày> <số khách> <hạng>` | `110 FLIGHTS <k>` rồi `k` dòng chuyến bay |
| `SEARCH <đi> <đến> <ngày> <số khách> <hạng> <ngày về>` | như trên, rồi `111 RETURN <m>` và `m` dòng chuyến bay chiều về |
| `QUIT` | `100 OK` rồi đóng kết nối |
| `QUIT` kèm tham số, hoặc `SEARCH` sai cú pháp | `201 INVALID` |
| mọi thứ khác (kể cả dòng trống, `search`, `LOGIN ...`) | `999 UNKNOWN ERROR` |

**Luật `SEARCH`** (đã học ở bài *fly-parse*): `đi` và `đến` là mã 3 chữ in hoa và khác nhau; ngày dạng `YYYY-MM-DD`
là ngày có thật (năm 1900–2100, kể cả năm nhuận); `số khách` là một chữ số `1`–`9`; `hạng` là `ECO` hoặc `BUS`;
`ngày về` hợp lệ và không trước `ngày đi`.

**Chuyến bay chiều đi:** các chuyến trong tệp có đúng `đi`, `đến`, `ngày đi` và hạng được chọn còn **ít nhất `số
khách`** ghế. **Chiều về:** như vậy nhưng đổi chỗ `đi`/`đến` và dùng `ngày về`. Mỗi dòng chuyến bay (theo thứ tự
trong tệp):

```
<mã> <hãng> <giờ đi> <giờ đến> <tổng tiền>        tổng tiền = giá hạng được chọn × số khách
```

## Ví dụ (với một `flights.txt` nhỏ)

```
→ SEARCH HAN SGN 2026-12-20 2 ECO
← 110 FLIGHTS 2
← VN213 VN 06:00 08:10 2500000
← VJ123 VJ 23:30 01:35 1780000
→ SEARCH HAN SGN 2026-12-20 1 BUS 2026-12-22
← 110 FLIGHTS 1
← VN213 VN 06:00 08:10 3500000
← 111 RETURN 0
→ SEARCH HAN SGN 2026-12-20 0 ECO
← 201 INVALID
→ PING
← 999 UNKNOWN ERROR
→ QUIT
← 100 OK
```

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu thật là `flights.txt` của bộ chấm (47 chuyến, 4 sân bay, 3 ngày), không phải ví dụ trên.
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng chục lệnh dính nhau trong một lần gửi; dòng cuối có thể là `\r\n`.
- Client im lặng hoặc gửi dở lệnh **không** được làm chậm client khác. Phục vụ ít nhất 30 client cùng lúc.
- Client có thể đóng đột ngột (RST) khi đang gửi dở; bộ chấm kết nối-ngắt 300 lần với giới hạn 256 file descriptor.
- Phản hồi nhiều dòng phải được gửi **liền nhau**, không xen lẫn với phản hồi lệnh khác của cùng client.

## Kiến thức nền
§4.3: thông điệp text, phản hồi có mã trạng thái, và **đếm trước số dòng** (`110 FLIGHTS k`) để client biết khi nào
hết dữ liệu. Ghép dòng cho từng client: xem `kv-max-n` / `chat-select`.
