---
title: "UDP: hướng thông điệp, không kết nối"
chapter: 2
ref: "Lecture notes §2.4 (tr.41); udp_receiver.c, udp_sender.c"
---

## Tóm tắt
UDP (`SOCK_DGRAM`) **không có kết nối**, không `listen`/`accept`/`connect` (client có thể `connect` nhưng chỉ để gắn sẵn địa chỉ đích). Mỗi `sendto` là một **datagram** độc lập, và `recvfrom` luôn nhận **đúng một** datagram: không gộp, không cắt nhỏ. Đổi lại không đảm bảo đến nơi, đúng thứ tự hay không trùng lặp.

## Server UDP
```c
int s = socket(AF_INET, SOCK_DGRAM, 0);
bind(s, (struct sockaddr *)&addr, sizeof addr);
for (;;) {
    char buf[65535];
    struct sockaddr_in from; socklen_t fl = sizeof from;
    ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&from, &fl);
    if (n < 0) continue;
    sendto(s, buf, n, 0, (struct sockaddr *)&from, fl);   // trả lời đúng địa chỉ nguồn
}
```

## Client UDP
```c
int s = socket(AF_INET, SOCK_DGRAM, 0);
sendto(s, msg, len, 0, (struct sockaddr *)&server, sizeof server);
recvfrom(s, buf, sizeof buf, 0, NULL, NULL);
```
Client không cần `bind`: hệ điều hành tự gán cổng khi gửi lần đầu.

## Phân biệt "client"
Không có kết nối nên server nhận diện client bằng **cặp (IP, cổng nguồn)** lấy từ `recvfrom`. Cần trạng thái theo từng client (đếm số datagram, phiên làm việc...) thì lưu bảng khoá theo cặp này.

## So sánh nhanh với TCP
| | TCP | UDP |
|---|---|---|
| Kết nối | có (3-way handshake) | không |
| Ranh giới thông điệp | không (luồng byte) | có (mỗi datagram) |
| Tin cậy / thứ tự | có | không |
| Kích thước tối đa | không giới hạn (luồng) | 65507 byte (IPv4) |
| Hàm gửi/nhận | `send`/`recv` | `sendto`/`recvfrom` |

## Bẫy thường gặp
- Bộ đệm `recvfrom` nhỏ hơn datagram → phần thừa bị **cắt bỏ âm thầm**, không báo lỗi.
- Datagram rỗng (0 byte) là hợp lệ, `recvfrom` trả `0` nhưng **không** có nghĩa là "đóng kết nối" như TCP.
- Dùng vòng `while (recv > 0)` kiểu TCP: UDP không có EOF.
- Trả lời bằng địa chỉ của chính server thay vì địa chỉ `from`.
- Nhầm `socklen_t` của `recvfrom`: phải khởi tạo `fl = sizeof from` **trước mỗi lần** gọi.
