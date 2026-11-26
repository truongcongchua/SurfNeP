# Giao diện web tìm chuyến bay (HTTP)

Tính năng nâng cao của bài tập lớn: **trang web** cho khách tìm chuyến bay bằng trình duyệt, viết bằng chính socket như `4-Chap4/http_server.c`
(mỗi kết nối một luồng, đọc yêu cầu đến `\r\n\r\n`, `sscanf` lấy method và path, gửi `Content-Length` đúng, đọc thân yêu cầu `POST` theo
`Content-Length`). Server nạp `flights.txt` (như bài *fly-search*) khi khởi động.

Viết `./server <cổng>`. Mỗi kết nối chỉ phục vụ **một** yêu cầu rồi đóng. Phải phục vụ nhiều kết nối cùng lúc (ít nhất 30): một trình duyệt
mở kết nối mà chưa gửi gì, hay gửi yêu cầu rất chậm, không được làm các kết nối khác chờ.

## Yêu cầu HTTP

Đọc cho đến khi gặp `\r\n\r\n` (tối đa 8 KB; yêu cầu có thể đến thành nhiều mảnh, kể cả bị cắt từng byte). Dòng đầu: `<METHOD> <TARGET> <VERSION>`
(đúng ba thành phần cách nhau một dấu cách). Các header khác có thể có hoặc không.

| Tình huống | Phản hồi |
|---|---|
| Dòng đầu không đủ 3 phần, hoặc `VERSION` không phải `HTTP/1.0` / `HTTP/1.1`, hoặc quá 8 KB mà chưa có `\r\n\r\n` | `400 Bad Request` |
| `METHOD` không phải `GET` hoặc `POST` (phân biệt hoa thường) | `405 Method Not Allowed` |
| Đường dẫn không có trong bảng dưới | `404 Not Found` |

**Đường dẫn** (`PATH` = phần của `TARGET` trước dấu `?` đầu tiên; không giải mã `%`):

| Yêu cầu | Phản hồi |
|---|---|
| `GET /` (kể cả `GET /?bat-ky`) | trang tìm kiếm (form) |
| `GET /search?<query>` hoặc `POST /search` với thân dạng `<query>` | kết quả tìm kiếm |
| `GET /flight/<mã chuyến>` | chi tiết một chuyến; không có chuyến → `404` |
| `POST` tới đường dẫn khác `/search`; `GET /search` không có tham số hợp lệ | xem dưới |

`POST` phải có header `Content-Length: <n>` (`0 ≤ n ≤ 4096`, không có hoặc sai → `400`); server đọc **đúng `n` byte** sau dòng trống (có thể đã nằm
sẵn trong lần `recv` đầu, hoặc đến sau). `Content-Type` được bỏ qua và tên header không phân biệt hoa thường. `POST /khac` → `404`.

**Query** là các cặp `khóa=giá trị` nối bằng `&`; giải mã `%XX` (hai chữ số hex, hoa hoặc thường) và `+` thành dấu cách. Khóa lặp lại thì lấy **lần đầu**; khóa lạ bị bỏ qua; thứ tự
tùy ý. Cần đủ 5 khóa `from`, `to`, `date`, `pax`, `class` và giá trị phải hợp lệ theo luật của bài *fly-parse* (mã sân bay 3 chữ in hoa khác nhau, ngày thật, `pax` 1–9, `class` là
`ECO` hoặc `BUS`) sau khi giải mã; thiếu, rỗng, sai, hoặc `%` hỏng (`%G1`, `%1` ở cuối) → `400 Bad Request`.

## Định dạng phản hồi

Mọi phản hồi có **đúng** các header sau, theo thứ tự này, mỗi dòng kết thúc `\r\n`:
```
HTTP/1.1 <mã> <lý do>
Content-Type: <kiểu>
Content-Length: <số byte thân>
Connection: close
```
rồi một dòng trống và thân. Trang HTML có kiểu `text/html; charset=utf-8`; phản hồi lỗi có kiểu `text/plain; charset=utf-8` và thân là lý do kèm `\n` (ví dụ `Not Found\n`).

### Trang tìm kiếm (`GET /`)
Thân là HTML phải chứa đủ: `<form action="/search" method="get">`, năm ô nhập `name="from"`, `name="to"`, `name="date"`, `name="pax"`, `name="class"` và `<input type="submit"`.

### Kết quả tìm kiếm
Thân phải chứa:
- `<h1>Co K chuyen</h1>` với `K` là số chuyến thỏa (luật lọc như *fly-search*: đúng đi, đến, ngày; hạng được chọn còn **ít nhất** `pax` ghế; tổng tiền = giá × `pax`);
- một bảng có đúng **một** dòng tiêu đề `<tr><th>Ma</th><th>Hang</th><th>Gio di</th><th>Gio den</th><th>Tong tien</th></tr>` và mỗi chuyến một dòng, theo thứ tự trong tệp:
  `<tr><td>VN213</td><td>VN</td><td>06:00</td><td>08:10</td><td>2500000</td></tr>`
  Không có chuyến nào thì **không** có dòng chuyến nào (vẫn có dòng tiêu đề).
Phần còn lại tùy bạn trình bày (CSS, đường dẫn tới `/flight/<mã>` ...), miễn không thêm thẻ `<tr>` nào khác.

### Chi tiết chuyến (`GET /flight/<mã>`)
Thân phải chứa: `<h1>VN213</h1>`, `<p>HAN -&gt; SGN 2026-12-20 06:00-08:10</p>` và hai dòng giá: `<p>ECO 1250000 (120 ghe)</p>` và `<p>BUS 3500000 (20 ghe)</p>`
(số liệu lấy từ `flights.txt`).

## Ví dụ

```
GET /search?from=HAN&to=SGN&date=2026-12-20&pax=2&class=ECO HTTP/1.1
Host: localhost

HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 412
Connection: close

<html>... <h1>Co 2 chuyen</h1> ... <tr><td>VN213</td>...</tr> ... </html>
```
```
POST /search HTTP/1.1
Content-Length: 56

from=HAN&to=SGN&date=2026-12-20&pax=2&class=ECO
```

## Ràng buộc và bộ chấm kiểm tra
- Dữ liệu thật là `flights.txt` của bộ chấm (47 chuyến). Bộ chấm phân tích thân HTML bằng biểu thức chính quy, nên đúng các chuỗi nêu trên là đủ.
- `Content-Length` phải bằng đúng số byte của thân (kể cả khi thân có ký tự `>` hay tiếng Việt không dấu).
- Client có thể đóng đột ngột khi chưa gửi xong yêu cầu; bộ chấm chạy 300 yêu cầu liên tiếp với giới hạn 256 file descriptor.
- Một số yêu cầu cố tình bị cắt đôi giữa `\r\n\r\n`, hoặc `POST` có thân đến chậm sau header.

## Kiến thức nền
`http_server.c`: `strstr(buffer, "\r\n\r\n")`, `sscanf(buffer, "%s%s", method, path)`, tìm `Content-Length` rồi `recv` đủ thân, `AppendStr`/`realloc` để dựng HTML,
`pthread_create` cho mỗi kết nối (cấp phát riêng giá trị fd cho luồng, đừng truyền địa chỉ biến của vòng `accept`).
