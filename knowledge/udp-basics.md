---
title: "UDP: hướng thông điệp, không kết nối"
chapter: 2
ref: "Lecture notes §2.4 (tr.41); udp_receiver.c, udp_sender.c"
---

## Hiểu nhanh
- **TCP** giống **gọi điện thoại**: phải kết nối trước, nói gì bên kia nghe đủ và đúng thứ tự.
- **UDP** giống **gửi bưu thiếp**: không cần kết nối, mỗi tấm ghi sẵn địa chỉ người nhận. Tấm nào đến thì đến nguyên vẹn, nhưng có thể **thất lạc**, **đến lộn thứ tự** hoặc **đến hai lần**.

Mỗi tấm bưu thiếp gọi là một **datagram**. Một lần `sendto` gửi đúng một datagram, một lần `recvfrom` nhận đúng một datagram: không bao giờ gộp hai tấm làm một hay xé một tấm làm hai.

## Server UDP
Không có `listen`, không có `accept`. Chỉ `socket` → `bind` → lặp `recvfrom`/`sendto`.
```c
int s = socket(AF_INET, SOCK_DGRAM, 0);              // SOCK_DGRAM = UDP
bind(s, (struct sockaddr *)&addr, sizeof addr);      // addr điền như thẻ "Địa chỉ socket"

for (;;) {
    char buf[65536];
    struct sockaddr_in from;                          // recvfrom sẽ ghi địa chỉ NGƯỜI GỬI vào đây
    socklen_t fromlen = sizeof from;                  // phải gán lại trước MỖI lần gọi
    ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&from, &fromlen);
    if (n < 0) continue;

    // trả lời: gửi về đúng địa chỉ vừa nhận được
    sendto(s, buf, n, 0, (struct sockaddr *)&from, fromlen);
}
```

## Client UDP
```c
int s = socket(AF_INET, SOCK_DGRAM, 0);
sendto(s, msg, len, 0, (struct sockaddr *)&server, sizeof server);   // server = địa chỉ server
ssize_t n = recvfrom(s, buf, sizeof buf, 0, NULL, NULL);            // không cần biết ai trả lời
```
Client **không cần `bind`**: lần `sendto` đầu tiên hệ điều hành tự chọn một cổng trống cho nó.

## Server phân biệt các client thế nào?
Không có kết nối nên không có "socket riêng cho từng client" như TCP. Server nhận ra client bằng **cặp (IP, cổng) người gửi** nằm trong `from`:
```c
char ip[INET_ADDRSTRLEN];
inet_ntop(AF_INET, &from.sin_addr, ip, sizeof ip);
int port = ntohs(from.sin_port);
// (ip, port) chính là "tên" của client này
```
Cần nhớ thông tin riêng cho từng client (đếm số tin, trạng thái...) thì lưu một bảng tra theo cặp này.

## So sánh với TCP
| | TCP | UDP |
|---|---|---|
| Kết nối trước khi gửi | có | không |
| Hàm | `send` / `recv` | `sendto` / `recvfrom` |
| Ranh giới thông điệp | **không** (luồng byte, có thể gộp/tách) | **có** (một datagram = một lần nhận) |
| Đảm bảo đến nơi, đúng thứ tự | có | không |
| Kích thước một lần gửi | tuỳ ý | tối đa 65507 byte |
| `recv` trả `0` nghĩa là | bên kia đã đóng | nhận được datagram rỗng (hợp lệ) |

## Lỗi hay gặp
- **Tin nhắn bị cụt mà không báo lỗi.** Bộ đệm `recvfrom` nhỏ hơn datagram, phần thừa bị **vứt bỏ**. Dùng bộ đệm đủ lớn (vd. 65536).
- **Server dừng khi nhận tin rỗng.** Viết vòng lặp kiểu TCP `while (recvfrom(...) > 0)`. UDP không có "đóng kết nối"; datagram 0 byte vẫn là một tin hợp lệ.
- **Client không nhận được trả lời.** Server `sendto` về địa chỉ của chính nó hoặc địa chỉ cố định, thay vì `from`.
- **Địa chỉ người gửi bị sai/cụt từ lần thứ hai.** Không gán lại `fromlen = sizeof from` trước mỗi lần `recvfrom`.
