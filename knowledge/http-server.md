---
title: "HTTP server từ socket thô (http_server.c)"
chapter: 4
ref: "Lecture notes §4.2.1; 4-Chap4/http_server.c; 3-Chap3/L2-LoopingServer/html.c"
---

## HTTP request/response gồm gì (§4.2.1)
```
GET /search?from=HAN&to=SGN HTTP/1.1\r\n     ← dòng đầu: METHOD  TARGET  VERSION
Host: localhost\r\n                         ← header, mỗi dòng "Tên: giá trị"
\r\n                                        ← dòng trống: hết header
(thân, chỉ có khi POST...)
```
Phản hồi: dòng trạng thái `HTTP/1.1 200 OK`, các header (bắt buộc có `Content-Length` nếu có thân), dòng trống, thân. HTTP là **stateless**: mỗi
request độc lập, server không nhớ request trước.

## Đọc request từ socket (như `http_server.c`)
TCP là luồng byte nên **phải đọc cho đến khi thấy `\r\n\r\n`**:
```c
char buffer[1024 * 1024] = {0};
int len = 0;
while (strstr(buffer, "\r\n\r\n") == NULL) {
    int r = recv(c, buffer + len, sizeof(buffer) - len - 1, 0);
    if (r <= 0) break;                 // client đóng giữa chừng
    len += r;
}
sscanf(buffer, "%s%s", method, path);  // lấy hai từ đầu: method và path
```
Cải tiến cần có cho một server dùng thật: đặt trần kích thước (8 KB cho header, quá thì `400`), kiểm tra `sscanf` đủ ba thành phần.

## Giải mã URL
Trình duyệt mã hóa ký tự đặc biệt: `%20` là dấu cách, `+` trong query cũng là dấu cách, `%41` là `A`. Code mẫu chỉ xử lý `%20` bằng `strstr` rồi
ghép lại; tổng quát hơn: duyệt từng ký tự, gặp `%` thì đổi hai chữ số hex tiếp theo bằng một hàm `hexv` (hoa hoặc thường), và coi `%` hỏng (`%G1`,
`%1` ở cuối chuỗi) là lỗi.

## Query string
`from=HAN&to=SGN&pax=2`: tách ở `&`, rồi mỗi cặp ở `=`, rồi giải mã **từng giá trị sau khi tách** (không giải mã trước, vì `%26` là ký tự `&` thật
nằm trong giá trị). Quy ước hay dùng: khóa lặp thì lấy lần đầu, khóa lạ thì bỏ qua.

## POST: đọc đủ thân
Header `Content-Length: n` cho biết thân dài bao nhiêu. Thân có thể đã nằm sẵn trong lần `recv` đầu (sau `\r\n\r\n`) hoặc đến sau:
```c
char *str = strstr(buffer, "Content-Length");      // http_server.c; tên header nên so không phân biệt hoa thường
int ctlen = 0; sscanf(str, "%s%d", text, &ctlen);
int received = len - (end_of_header - buffer);     // phần thân đã có
while (received < ctlen) { int r = recv(c, data + received, ctlen - received, 0); if (r <= 0) break; received += r; }
```
Trần cho `n` (4096) và kiểm tra `n >= 0`: **không** cấp phát bộ nhớ theo con số client tự khai báo mà không giới hạn.

## Gửi phản hồi
```c
snprintf(head, sizeof head, "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n", n);
send(c, head, strlen(head), 0);
send(c, body, n, 0);
```
`Content-Length` phải bằng **đúng số byte** của thân (đếm bằng giá trị trả về của `snprintf`, không dùng `strlen` nếu thân là nhị phân). Dựng HTML dài
bằng `realloc` (hàm `AppendStr` trong `http_server.c`) hoặc một bộ đệm lớn rồi `snprintf` nối tiếp.

## Mỗi kết nối một luồng
```c
int *param = calloc(1, sizeof(int));   // cấp phát riêng cho luồng
*param = c;
pthread_create(&tid, NULL, ClientThread, param);
pthread_detach(tid);                    // luồng tự giải phóng tài nguyên khi xong
```
Truyền `&c` (biến cục bộ của vòng `accept`) là lỗi: vòng sau ghi đè giá trị trước khi luồng cũ kịp đọc. `http_server.c` quên `pthread_detach`
(luồng kết thúc nhưng không được dọn), và không `free` tham số: nên sửa cả hai.

## Mã trạng thái nên có
`200 OK`, `400 Bad Request` (yêu cầu sai khuôn), `404 Not Found`, `405 Method Not Allowed` (method lạ). Nhóm 4xx là lỗi của client, 5xx của server (§4.2.1).
