# Server lặp phục vụ tệp qua HTTP

Viết web server tối giản `./server <cổng> <thư mục gốc>`, hoạt động theo **cơ chế lặp**: nhận một
kết nối, xử lý **một** yêu cầu HTTP, trả lời, **đóng** kết nối rồi `accept` kết nối tiếp theo.

## Yêu cầu
Đọc yêu cầu cho đến khi gặp dòng trống `\r\n\r\n` (yêu cầu có thể đến thành **nhiều mảnh**; tối đa
8 KB). Dòng đầu có dạng `<METHOD> <PATH> <VERSION>`.

| Trường hợp | Mã trạng thái |
|---|---|
| Dòng đầu không đủ 3 phần | `400 Bad Request` |
| METHOD khác `GET` | `405 Method Not Allowed` |
| PATH chứa `..` | `403 Forbidden` |
| Tệp không tồn tại hoặc không phải tệp thường | `404 Not Found` |
| Còn lại | `200 OK` + nội dung tệp |

- Bỏ phần query sau `?`. PATH kết thúc bằng `/` thì phục vụ `index.html` trong thư mục đó.
- Phản hồi luôn có **đúng** các header sau, theo thứ tự này, mỗi dòng kết thúc bằng `\r\n`:
  ```
  HTTP/1.1 <mã> <lý do>
  Content-Type: <kiểu>
  Content-Length: <số byte thân>
  Connection: close
  ```
  rồi một dòng trống, rồi thân.
- Kiểu theo đuôi tệp: `.html` → `text/html; charset=utf-8`, `.txt` → `text/plain; charset=utf-8`,
  `.png` → `image/png`, còn lại `application/octet-stream`.
- Phản hồi lỗi có thân là lý do kèm `\n` (ví dụ `Not Found\n`), kiểu `text/plain; charset=utf-8`.

## Ràng buộc và bộ chấm kiểm tra
- Yêu cầu tối đa 8 KB; dòng đầu có thể dài tới 4 KB (query rất dài); dòng trống `\r\n\r\n` có thể bị cắt giữa hai
  lần gửi. Dữ liệu sau dòng trống bị bỏ qua; mỗi kết nối chỉ trả lời **một** yêu cầu.
- `..` ở **bất kỳ đâu** trong PATH (sau khi bỏ query) → 403, kể cả `/a..b.txt`. METHOD phân biệt hoa thường.
- Kiểu nội dung xét theo **đuôi cuối cùng**, phân biệt hoa thường (`b.HTML`, `a.htm` → `application/octet-stream`).
- Tệp có thể rỗng hoặc lớn tới 1 MB dữ liệu nhị phân: `Content-Length` là số byte thật.
- Client có thể đóng đột ngột khi chưa gửi xong yêu cầu. Chương trình chạy với giới hạn 256 file descriptor
  (300 yêu cầu liên tiếp).

## Ví dụ

```
GET /docs/note.txt HTTP/1.1\r\nHost: x\r\n\r\n
→ HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 32\r\nConnection: close\r\n\r\n<32 byte nội dung tệp>
```

## Suy ngẫm
Mở hai cửa sổ: một cái `nc localhost <cổng>` rồi để im, cái kia dùng trình duyệt. Chuyện gì xảy ra?
Đó chính là giới hạn của server lặp, và là lý do cần đến các kỹ thuật ở §3.3–3.5.
