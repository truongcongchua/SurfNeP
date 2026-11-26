# Lọc chuyến bay từ tệp

Bài khởi động cho chức năng **tìm kiếm chuyến bay** của bài tập lớn đặt vé máy bay. Chưa có mạng: chương trình
nạp danh sách chuyến bay từ tệp `flights.txt` (nằm trong thư mục hiện hành) vào bộ nhớ, rồi trả lời các truy vấn
đọc từ `stdin`.

## Tệp `flights.txt`

Mỗi dòng là một chuyến bay, 11 trường cách nhau bởi đúng một dấu cách:

```
<mã> <hãng> <đi> <đến> <ngày> <giờ đi> <giờ đến> <giá ECO> <ghế ECO> <giá BUS> <ghế BUS>
VN213 VN HAN SGN 2026-12-20 06:00 08:10 1250000 120 3500000 20
```

- `giá` là số nguyên đồng cho **một** khách; `ghế` là số ghế còn trống của hạng đó.
- Tệp có tối đa 1000 dòng, mã chuyến là duy nhất.

## Truy vấn

Mỗi dòng `stdin` là một truy vấn (luôn hợp lệ):

```
<đi> <đến> <ngày> <số khách> <hạng>
HAN SGN 2026-12-20 2 ECO
```

Với mỗi truy vấn in **đúng** các chuyến thỏa mãn **tất cả**: cùng sân bay đi, sân bay đến, ngày, và hạng được chọn còn
**ít nhất `số khách`** ghế. In theo thứ tự các chuyến xuất hiện trong tệp:

```
110 FLIGHTS <k>
<mã> <hãng> <giờ đi> <giờ đến> <tổng tiền>      (k dòng)
```

`tổng tiền` = giá của hạng được chọn × số khách. Không có chuyến nào thì chỉ in `110 FLIGHTS 0`.
Dòng truy vấn trống thì bỏ qua (không in gì).

## Ví dụ

Với `flights.txt`:
```
VN213 VN HAN SGN 2026-12-20 06:00 08:10 1250000 120 3500000 20
VJ123 VJ HAN SGN 2026-12-20 23:30 01:35 890000 3 0 0
QH777 QH HAN SGN 2026-12-21 09:00 11:05 1100000 50 0 0
```
Đầu vào:
```
HAN SGN 2026-12-20 2 ECO
HAN SGN 2026-12-20 4 ECO
HAN SGN 2026-12-20 1 BUS
SGN HAN 2026-12-20 1 ECO
```
Đầu ra:
```
110 FLIGHTS 2
VN213 VN 06:00 08:10 2500000
VJ123 VJ 23:30 01:35 1780000
110 FLIGHTS 1
VN213 VN 06:00 08:10 5000000
110 FLIGHTS 1
VN213 VN 06:00 08:10 3500000
110 FLIGHTS 0
```
(Truy vấn thứ hai loại `VJ123` vì chỉ còn 3 ghế ECO, ít hơn 4 khách.)

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu thật nằm trong `flights.txt` của bộ chấm (không phải ví dụ trên). Có đủ loại chuyến: qua nửa đêm, hết ghế
  hạng BUS, đúng bằng số ghế yêu cầu, và một tuyến có hơn 60 chuyến trong cùng một ngày.
- Số khách từ 1 đến 9; giá không quá 10^8, nên tổng tiền không quá 9 × 10^8.
- Có thể có hàng chục nghìn truy vấn; dòng truy vấn có thể kết thúc bằng `\r\n`, dòng cuối có thể không có `\n`.
- Đọc lại tệp cho mỗi truy vấn sẽ quá chậm: hãy nạp **một lần** vào mảng.

## Kiến thức nền
`fopen`, `fgets`, `sscanf` (lab07); mảng `struct` (lab10). Đây chính là bước "đọc dữ liệu chuyến bay" của server
trong bài tập lớn.
