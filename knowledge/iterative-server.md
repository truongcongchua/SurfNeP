---
title: "Server lặp & thiết kế giao thức ứng dụng"
chapter: 3
ref: "Lecture notes §3.2 (tr.53); §4.2.1 HTTP; L2-LoopingServer/html.c"
---

## Hiểu nhanh
**Server lặp** (iterative server) giống **quầy giao dịch chỉ có một nhân viên**: phục vụ xong khách này mới gọi khách tiếp theo.
- Ưu: code đơn giản nhất, không phải lo hai khách tranh nhau dữ liệu.
- Nhược: khách sau phải chờ; một khách chậm (hoặc không nói gì) làm cả hàng đứng im.

Hợp với dịch vụ **hỏi một câu, trả lời một câu rồi đóng**, như HTTP đơn giản.

```c
for (;;) {
    int fd = accept(listen_fd, NULL, NULL);   // gọi khách tiếp theo
    if (fd < 0) continue;
    handle_one_request(fd);                    // phục vụ trọn vẹn
    close(fd);                                 // tiễn khách
}
```

## Giao thức là gì?
**Giao thức** = luật nói chuyện mà client và server cùng tuân theo: ai nói trước, nói theo mẫu nào, trả lời ra sao. Trước khi code, trả lời 4 câu:
1. **Thông điệp kết thúc ở đâu?** (vd. mỗi lệnh một dòng `\n`; HTTP thì header kết thúc ở dòng trống `\r\n\r\n`). Xem thẻ *TCP là luồng byte*.
2. **Một lệnh trông thế nào?** vd. `LENH thamso1 thamso2\n`, tách bằng `sscanf` hoặc `strtok`.
3. **Trả lời thế nào?** Khi thành công và **từng loại lỗi** trả về gì.
4. **Trường hợp lạ thì sao?** Thiếu/thừa tham số, dòng quá dài, client đóng giữa chừng.

```c
char cmd[16], arg[256];
int k = sscanf(line, "%15s %255s", cmd, arg);   // k = số phần đọc được
if (k < 1)                     send_str(fd, "ERROR empty\n");
else if (!strcmp(cmd, "GET") && k == 2) { /* ... */ }
else                           send_str(fd, "ERROR unknown\n");
```

## Ví dụ: HTTP tối giản
Trình duyệt gửi (mỗi dòng kết thúc bằng `\r\n`, cuối cùng là một dòng trống):
```
GET /index.html HTTP/1.1
Host: localhost:8080

```
Dòng đầu gồm 3 phần: **phương thức** (`GET`), **đường dẫn** (`/index.html`), **phiên bản**. Tách bằng:
```c
char method[8], path[256], ver[16];
sscanf(request, "%7s %255s %15s", method, path, ver);
```

Server trả lời:
```
HTTP/1.1 200 OK\r\n
Content-Type: text/html; charset=utf-8\r\n
Content-Length: 123\r\n          ← số byte của phần thân
Connection: close\r\n
\r\n                             ← dòng trống ngăn header và thân
<nội dung trang>
```
- `Content-Length` phải là **số byte thật** của thân. Sai thì trình duyệt chờ mãi hoặc cắt cụt.
- Dòng trống là `\r\n` (2 ký tự), không phải chỉ `\n`.
- Một số mã trạng thái: `200 OK`, `400 Bad Request` (yêu cầu sai cú pháp), `403 Forbidden` (không cho phép), `404 Not Found` (không có tệp), `405 Method Not Allowed` (không hỗ trợ phương thức).

## Lỗi hay gặp
- **Yêu cầu đến làm nhiều mảnh thì phân tích sai.** Chỉ `recv` một lần. Sửa: nhận dồn đến khi thấy `\r\n\r\n`.
- **Đường dẫn chứa `..` lọt ra ngoài thư mục gốc.** Phải chặn `..`, và kiểm tra **sau khi** đã bỏ phần `?query`.
- **Trình duyệt quay mãi không hiện trang.** Sai `Content-Length`, thiếu dòng trống, hoặc quên `close(fd)` dù đã báo `Connection: close`.
- **Sai mã lỗi.** Khi một yêu cầu vi phạm nhiều điều, phải kiểm tra **đúng thứ tự** đề yêu cầu (vd. 400 → 405 → 403 → 404).
