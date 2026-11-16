---
title: "Địa chỉ socket & phân giải tên miền"
chapter: 2
ref: "Lecture notes §2.2 (tr.16)"
---

## Tóm tắt
Địa chỉ IPv4 + cổng được đặt trong `struct sockaddr_in`. Các hàm socket nhận con trỏ `struct sockaddr *` nên phải **ép kiểu** và truyền kèm độ dài.

```c
#include <arpa/inet.h>
struct sockaddr_in addr;
memset(&addr, 0, sizeof addr);          // xoá sạch, tránh rác ở sin_zero
addr.sin_family = AF_INET;
addr.sin_port   = htons(8080);          // cổng luôn ở network byte order
inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);   // xâu -> nhị phân
```

## Hàm cần nhớ
| Hàm | Việc làm | Trả về |
|---|---|---|
| `inet_pton(af, src, dst)` | xâu → nhị phân | `1` hợp lệ, `0` sai định dạng, `-1` lỗi |
| `inet_ntop(af, src, dst, size)` | nhị phân → xâu | con trỏ `dst`, `NULL` nếu lỗi |
| `getaddrinfo(host, service, &hints, &res)` | tên miền → danh sách địa chỉ | `0` thành công, khác `0` là mã lỗi (đọc bằng `gai_strerror`) |
| `freeaddrinfo(res)` | giải phóng danh sách | |

Server muốn nghe trên mọi giao diện: `addr.sin_addr.s_addr = htonl(INADDR_ANY);`

## Phân giải tên miền
`getaddrinfo` trả về **danh sách liên kết** (`ai_next`): một tên miền có thể có nhiều địa chỉ. Duyệt hết rồi `freeaddrinfo`.

```c
struct addrinfo hints = {0}, *res, *p;
hints.ai_family = AF_INET;
hints.ai_socktype = SOCK_STREAM;
if (getaddrinfo("example.com", NULL, &hints, &res) != 0) { /* lỗi */ }
for (p = res; p; p = p->ai_next) {
    char ip[INET_ADDRSTRLEN];
    struct sockaddr_in *a = (struct sockaddr_in *)p->ai_addr;
    inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
}
freeaddrinfo(res);
```

## Bẫy thường gặp
- Quên `htons` cho cổng → kết nối nhầm cổng (8080 thành 36895 trên máy little-endian).
- Không kiểm tra giá trị trả về của `inet_pton`: `0` nghĩa là xâu **không phải** IP hợp lệ, không phải lỗi hệ thống.
- Dùng `inet_ntoa` (không an toàn luồng, chỉ IPv4); ưu tiên `inet_ntop`.
- Quên `freeaddrinfo` (rò rỉ bộ nhớ).
