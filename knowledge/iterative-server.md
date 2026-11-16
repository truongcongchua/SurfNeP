---
title: "Server lặp & thiết kế giao thức ứng dụng"
chapter: 3
ref: "Lecture notes §3.2 (tr.53); §4.2.1 HTTP; L2-LoopingServer/html.c"
---

## Server lặp (iterative)
Phục vụ **một client xong mới `accept` client tiếp**. Code đơn giản, không cần đồng bộ, nhưng client sau phải chờ; một client chậm hoặc treo sẽ chặn cả server.

```c
for (;;) {
    int fd = accept(s, NULL, NULL);
    handle_one_request(fd);
    close(fd);                 // HTTP/1.0 kiểu "Connection: close"
}
```
Phù hợp: dịch vụ ngắn (HTTP một yêu cầu, trả lời rồi đóng).

## Thiết kế một giao thức văn bản
Trả lời 4 câu hỏi trước khi code:
1. **Đóng khung:** thông điệp kết thúc ở đâu? (HTTP: `\r\n\r\n` kết thúc header)
2. **Cú pháp:** `<LỆNH> <tham số...>\n`, tách bằng `sscanf`/`strtok`.
3. **Phản hồi:** thành công và từng loại lỗi (mã trạng thái / `ERROR`).
4. **Hành vi biên:** lệnh thiếu/thừa tham số, quá dài, client đóng giữa chừng.

## Ví dụ: xử lý yêu cầu HTTP tối giản
```
GET /index.html HTTP/1.1\r\n
Host: ...\r\n
\r\n
```
Dòng đầu: `METHOD PATH VERSION`. Phản hồi:
```
HTTP/1.1 200 OK\r\n
Content-Type: text/html; charset=utf-8\r\n
Content-Length: <số byte thân>\r\n
Connection: close\r\n
\r\n
<thân>
```
`Content-Length` phải là **số byte thật** của thân, nếu sai trình duyệt sẽ treo hoặc cắt cụt.

## Bẫy thường gặp
- Chỉ `recv` một lần rồi phân tích → yêu cầu đến thành nhiều mảnh thì hỏng (xem thẻ *TCP là luồng byte*).
- Kiểm tra `..` trong đường dẫn nhưng bỏ sót trường hợp sau khi cắt phần `?query`.
- Dòng trống giữa header và thân phải là **`\r\n\r\n`** (HTTP dùng CRLF, không chỉ `\n`).
- Quên `close` sau mỗi yêu cầu khi đã khai báo `Connection: close`.
- Thứ tự kiểm tra lỗi (400 → 405 → 403 → 404) khác đề yêu cầu.
