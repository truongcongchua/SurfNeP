# So sánh giá vé và thời gian bay

Chức năng "so sánh giá vé và thời gian bay của các hãng" trong bài tập lớn đặt vé máy bay. Chưa có mạng: đọc danh sách
chuyến bay từ `flights.txt` (định dạng và cách lọc như bài *flight-filter*), rồi trả lời các truy vấn từ `stdin`. Phần mạng sau
này chỉ là gắn thêm hai lệnh này vào server của bài *fly-search*.

## Thời gian bay

`phút bay` = `giờ đến` − `giờ đi` tính bằng phút; nếu kết quả **không dương** thì cộng thêm 1440 (hạ cánh sang ngày hôm sau). Ví dụ
`23:30 → 01:00` là 90 phút.

## Chuyến "thỏa" một truy vấn

Chuyến khớp sân bay đi, sân bay đến, ngày và hạng được chọn còn **ít nhất `số khách`** ghế (như *flight-filter*).
`tổng tiền` = giá hạng được chọn × số khách.

## Lệnh

Mỗi dòng `stdin` là một lệnh, các thành phần cách nhau bởi một dấu cách. Dòng trống bị bỏ qua (bỏ `\r` cuối dòng).

**`COMPARE <đi> <đến> <ngày> <số khách> <hạng> <tiêu chí>`** với `tiêu chí` là `PRICE`, `DURATION` hoặc `DEPART`. In
các chuyến thỏa, đã **sắp xếp tăng dần**:
```
110 FLIGHTS <k>
<mã> <hãng> <giờ đi> <giờ đến> <phút bay> <tổng tiền>        (k dòng)
```
| Tiêu chí | Khóa sắp xếp (hòa thì xét tiếp khóa sau) |
|---|---|
| `PRICE` | tổng tiền (số), rồi phút bay (số), rồi mã chuyến |
| `DURATION` | phút bay (số), rồi tổng tiền (số), rồi mã chuyến |
| `DEPART` | giờ đi (`HH:MM`), rồi mã chuyến |

Mã chuyến so sánh theo thứ tự từ điển (`strcmp`). `tiêu chí` khác ba giá trị trên → `201 INVALID`.

**`BEST <đi> <đến> <ngày> <số khách> <hạng>`**: với **mỗi hãng** có ít nhất một chuyến thỏa, tìm chuyến **rẻ nhất** (theo tổng tiền,
hòa thì mã nhỏ hơn) và chuyến **nhanh nhất** (theo phút bay, hòa thì mã nhỏ hơn). In theo thứ tự mã hãng tăng dần:
```
110 AIRLINES <m>
<hãng> CHEAPEST <mã> <tổng tiền> FASTEST <mã> <phút bay>        (m dòng)
```

Không có chuyến nào thì chỉ in `110 FLIGHTS 0` hoặc `110 AIRLINES 0`. Tên lệnh khác `COMPARE` và `BEST` (phân biệt hoa thường)
→ `999 UNKNOWN ERROR`. Với `COMPARE`/`BEST`, mọi thành phần khác (sân bay, ngày, số khách, hạng) luôn hợp lệ và đủ số lượng; chỉ riêng
`tiêu chí` và tên lệnh có thể sai.

## Ví dụ

`flights.txt`:
```
VN1 VN HAN SGN 2026-12-20 06:00 08:10 1250000 120 3500000 20
VJ1 VJ HAN SGN 2026-12-20 23:30 01:35 890000 3 0 0
VJ2 VJ HAN SGN 2026-12-20 10:00 12:05 950000 50 0 0
```
Đầu vào:
```
COMPARE HAN SGN 2026-12-20 2 ECO PRICE
COMPARE HAN SGN 2026-12-20 1 ECO DEPART
BEST HAN SGN 2026-12-20 1 ECO
COMPARE HAN SGN 2026-12-20 1 ECO LOWEST
```
Đầu ra:
```
110 FLIGHTS 3
VJ1 VJ 23:30 01:35 125 1780000
VJ2 VJ 10:00 12:05 125 1900000
VN1 VN 06:00 08:10 130 2500000
110 FLIGHTS 3
VN1 VN 06:00 08:10 130 1250000
VJ2 VJ 10:00 12:05 125 950000
VJ1 VJ 23:30 01:35 125 890000
110 AIRLINES 2
VJ CHEAPEST VJ1 890000 FASTEST VJ1 125
VN CHEAPEST VN1 1250000 FASTEST VN1 130
201 INVALID
```
(Với `DEPART`, `06:00` đứng trước `10:00` và `23:30`.)

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu thật là `flights.txt` của bộ chấm (322 chuyến, có chuyến qua nửa đêm, có chuyến hòa giá / hòa giờ bay / cùng giờ đi giữa các hãng).
- So sánh **số** bằng số, không phải bằng chuỗi (`900000` đứng trước `1000000`). Tổng tiền dùng `long long`.
- Có thể có hàng chục nghìn truy vấn; dòng có thể kết thúc `\r\n`, dòng cuối có thể không có `\n`.
- Nạp tệp một lần, sắp xếp bằng `qsort` với hàm so sánh của bạn (con trỏ hàm, lab05).

## Kiến thức nền
`qsort` và hàm so sánh `int cmp(const void *a, const void *b)` (lab05, con trỏ hàm); đọc tệp `fopen`/`fgets`/`sscanf` (lab07).
`qsort` không ổn định theo chuẩn, nên **mọi** trường hợp hòa phải được phân định bằng khóa phụ như bảng trên.
