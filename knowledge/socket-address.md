---
title: "Địa chỉ socket & phân giải tên miền"
chapter: 2
ref: "Lecture notes §2.2 (tr.16)"
---

## Hiểu nhanh
Để gửi thư cần **địa chỉ nhà + số phòng**. Trên mạng cũng vậy:
- **Địa chỉ IP** (vd. `127.0.0.1`) = địa chỉ nhà: chỉ ra máy nào.
- **Cổng** (vd. `8080`) = số phòng: chỉ ra chương trình nào trên máy đó.

Trong C, cặp (IP, cổng) IPv4 được cất trong một struct tên `struct sockaddr_in`.

## Điền một địa chỉ
```c
#include <string.h>
#include <arpa/inet.h>

struct sockaddr_in addr;
memset(&addr, 0, sizeof addr);           // xoá sạch trước, tránh giá trị rác
addr.sin_family = AF_INET;               // AF_INET = IPv4
addr.sin_port   = htons(8080);           // cổng: PHẢI qua htons (xem thẻ "Thứ tự byte")
inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);   // xâu "127.0.0.1" → 4 byte máy hiểu
```

Server muốn nhận kết nối trên **mọi** địa chỉ IP của máy thì không cần `inet_pton`:
```c
addr.sin_addr.s_addr = htonl(INADDR_ANY);
```

**Vì sao phải ép kiểu `(struct sockaddr *)&addr`?** Các hàm `bind`, `connect`, `accept`... được viết chung cho nhiều loại địa chỉ (IPv4, IPv6...), nên nhận kiểu chung `struct sockaddr *` kèm **độ dài** struct. Bạn chỉ việc ép kiểu và truyền `sizeof addr`.

## Đổi qua lại giữa xâu và dạng nhị phân
| Hàm | Việc làm | Trả về |
|---|---|---|
| `inet_pton(AF_INET, "1.2.3.4", &addr.sin_addr)` | xâu → nhị phân (**p**resentation **to** **n**etwork) | `1` hợp lệ, `0` xâu không phải IP, `-1` lỗi |
| `inet_ntop(AF_INET, &addr.sin_addr, buf, sizeof buf)` | nhị phân → xâu | `buf`, hoặc `NULL` nếu lỗi |

Dùng `inet_pton` để **kiểm tra một xâu có phải IP hợp lệ không**: trả `1` là hợp lệ.
```c
struct in_addr tmp;
if (inet_pton(AF_INET, s, &tmp) == 1) printf("IP hop le\n");
else                                  printf("IP khong hop le\n");
```

Bộ đệm cho `inet_ntop` nên khai báo `char ip[INET_ADDRSTRLEN];` (đủ chỗ cho `"255.255.255.255"` và `'\0'`).

## Phân giải tên miền: `getaddrinfo`
Con người nhớ tên (`example.com`), máy cần IP. `getaddrinfo` hỏi DNS và trả về **danh sách** địa chỉ, vì một tên miền có thể có nhiều IP.

```c
#include <netdb.h>

struct addrinfo hints = {0}, *res, *p;
hints.ai_family   = AF_INET;          // chỉ lấy IPv4
hints.ai_socktype = SOCK_STREAM;      // để mỗi IP chỉ xuất hiện một lần

int err = getaddrinfo("example.com", NULL, &hints, &res);
if (err != 0) {
    printf("Loi: %s\n", gai_strerror(err));   // gai_strerror đổi mã lỗi thành câu chữ
    return;
}
for (p = res; p != NULL; p = p->ai_next) {    // duyệt danh sách liên kết
    struct sockaddr_in *a = (struct sockaddr_in *)p->ai_addr;
    char ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &a->sin_addr, ip, sizeof ip);
    printf("%s\n", ip);
}
freeaddrinfo(res);                            // trả lại bộ nhớ khi dùng xong
```

Lưu ý: `getaddrinfo` trả `0` là **thành công** (ngược với thói quen "0 là sai").

## Lỗi hay gặp
- **Kết nối nhầm cổng** (vd. 8080 thành 36895). Quên `htons` khi gán `sin_port`.
- **Báo "IP hợp lệ" cho xâu sai.** Viết `if (inet_pton(...))`: kết quả `-1` cũng là "đúng" trong C. Sửa: so sánh `== 1`.
- **Struct có giá trị lạ, `bind`/`connect` lỗi khó hiểu.** Quên `memset` (hoặc `= {0}`) trước khi điền.
- **Rò rỉ bộ nhớ.** Quên `freeaddrinfo(res)`.
- Tránh dùng `inet_ntoa`/`gethostbyname`: hàm cũ, không an toàn khi dùng nhiều luồng. Dùng `inet_ntop`/`getaddrinfo`.
