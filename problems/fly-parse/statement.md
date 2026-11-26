# Kiểm tra cú pháp lệnh FLY

Đây là bài khởi động cho bài tập lớn **đặt vé máy bay**. Server của bạn sẽ nhận các lệnh text một dòng như
`LOGIN an 1234` hay `SEARCH HAN SGN 2026-12-20 2 ECO`. Trước khi xử lý, server phải kiểm tra **cú pháp** của lệnh.
Bài này chỉ làm đúng việc đó, **chưa có mạng**: đọc từng dòng từ `stdin`, in một dòng kết quả cho mỗi lệnh.

## Kết quả cho mỗi dòng

| Điều kiện | In ra |
|---|---|
| Dòng trống (sau khi bỏ `\r` cuối dòng) | *không in gì* |
| Tên lệnh không phải `REGISTER`, `LOGIN`, `SEARCH` (phân biệt hoa thường) | `999 UNKNOWN ERROR` |
| Tên lệnh đúng nhưng các tham số sai luật bên dưới | `201 INVALID` |
| Tên lệnh đúng và mọi tham số đúng | `100 OK` |

## Cách tách dòng

Các thành phần cách nhau bởi **đúng một dấu cách**. Dấu cách thừa (đầu dòng, cuối dòng, hai dấu cách liền nhau)
tạo ra thành phần rỗng, và thành phần rỗng luôn là sai. Tab không phải dấu cách. Bỏ **đúng một** ký tự `\r` ở
cuối dòng (nếu có) trước khi xét.

## Các lệnh

**`REGISTER <user> <pass>`** và **`LOGIN <user> <pass>`**: đúng 3 thành phần.
- `user`: 1–32 ký tự, mỗi ký tự là chữ thường `a-z` hoặc chữ số `0-9`.
- `pass`: 4–32 ký tự, mỗi ký tự có mã từ `0x21` (`!`) đến `0x7E` (`~`).

**`SEARCH <đi> <đến> <ngày đi> <số khách> <hạng> [<ngày về>]`**: đúng 6 hoặc 7 thành phần.
- `đi`, `đến`: đúng 3 chữ cái in hoa `A-Z` (mã sân bay), và hai mã **khác nhau**.
- Ngày có dạng `YYYY-MM-DD`, là **ngày có thật** trong lịch (tháng có số ngày đúng, năm nhuận đúng) và năm từ
  1900 đến 2100. Ví dụ `2024-02-29` hợp lệ, `2100-02-29` và `2026-02-29` không hợp lệ.
- `số khách`: đúng một chữ số từ `1` đến `9`.
- `hạng`: `ECO` hoặc `BUS`.
- `ngày về` (nếu có): ngày hợp lệ và **không trước** `ngày đi` (cho phép bằng nhau).

## Ví dụ

Đầu vào:
```
LOGIN an 1234
LOGIN An 1234
SEARCH HAN SGN 2026-12-20 2 ECO
SEARCH HAN HAN 2026-12-20 2 ECO

SEARCH HAN SGN 2026-12-20 2 ECO 2026-12-19
PING
```
Đầu ra:
```
100 OK
201 INVALID
100 OK
201 INVALID
201 INVALID
999 UNKNOWN ERROR
```

## Ràng buộc
- Mỗi dòng tối đa 4000 byte; có thể kết thúc bằng `\r\n`; dòng cuối có thể không có `\n`.
- Đầu vào có thể chứa byte lạ (mã ≥ 0x80, mã điều khiển) nhưng không chứa byte `0x00`.
- Không dùng `strtok`: nó coi nhiều dấu cách liền nhau là một và làm mất thành phần rỗng.

## Kiến thức nền
§4.3: thiết kế giao thức bắt đầu từ việc định nghĩa chính xác **định dạng thông điệp**. Thao tác với xâu: lab09
(`strchr`, `strlen`, `strcmp`, `sscanf`).
