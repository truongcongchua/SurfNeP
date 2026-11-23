---
title: "Địa chỉ socket & phân giải tên miền"
chapter: 2
ref: "Lecture notes §2.2 (tr.16); 2-Chap2/tcp_client.c, udp_receiver.c, domain2ip.c"
---

## Hiểu nhanh
Để gửi thư cần **địa chỉ nhà + số phòng**. Trên mạng cũng vậy:
- **Địa chỉ IP** (vd. `127.0.0.1`) = địa chỉ nhà: chỉ ra máy nào.
- **Cổng** (vd. `8080`) = số phòng: chỉ ra chương trình nào trên máy đó.

Trong C, cặp (IP, cổng) IPv4 được cất trong một struct tên `struct sockaddr_in`.

## Điền một địa chỉ
Như `tcp_client.c`:
```c
#include <arpa/inet.h>

struct sockaddr_in addr;
addr.sin_family = AF_INET;                       // AF_INET = IPv4
addr.sin_port = htons(8080);                     // cổng: PHẢI qua htons (xem thẻ "Thứ tự byte")
addr.sin_addr.s_addr = inet_addr("127.0.0.1");   // xâu "127.0.0.1" → 4 byte (thứ tự mạng)
```

Server muốn nhận kết nối trên **mọi** địa chỉ IP của máy thì dùng `INADDR_ANY` (như `tcp_server.c`):
```c
addr.sin_addr.s_addr = INADDR_ANY;
```

**Vì sao phải ép kiểu `(struct sockaddr *)&addr`?** Các hàm `bind`, `connect`, `accept`... được viết chung cho nhiều loại địa chỉ (IPv4, IPv6...), nên nhận kiểu chung `struct sockaddr *` kèm **độ dài** struct. Bạn chỉ việc ép kiểu và truyền `sizeof(addr)`.

## Đổi qua lại giữa xâu và dạng nhị phân
| Hàm | Việc làm | Trả về |
|---|---|---|
| `inet_addr("1.2.3.4")` | xâu → nhị phân (thứ tự mạng) | giá trị `s_addr`, hoặc `INADDR_NONE` nếu xâu sai |
| `inet_ntoa(addr.sin_addr)` | nhị phân → xâu | con trỏ tới xâu, vd. `"1.2.3.4"` |

Lấy IP của người gửi như `udp_receiver.c`:
```c
printf("Client IP: %s, Port: %d\n", inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));
```

`inet_addr` có một điểm khó chịu: giá trị lỗi `INADDR_NONE` (`0xFFFFFFFF`) **trùng** với địa chỉ hợp lệ `255.255.255.255`. Muốn kiểm tra một xâu, so riêng trường hợp đó:
```c
in_addr_t a = inet_addr(s);
if (a == INADDR_NONE && strcmp(s, "255.255.255.255") != 0) printf("IP khong hop le\n");
```
`inet_addr` cũng khá dễ dãi: nhận dạng viết tắt (`10.1` là `10.0.0.1`), số bát phân (`010`) và số hex (`0x7f`).

## Phân giải tên miền: `getaddrinfo`
Con người nhớ tên (`example.com`), máy cần IP. `getaddrinfo` hỏi DNS và trả về **danh sách** địa chỉ, vì một tên miền có thể có nhiều IP. Như `domain2ip.c`:

```c
#include <netdb.h>

struct addrinfo *res, *p;
int ret = getaddrinfo("example.com", "http", NULL, &res);
if (ret != 0 || res == NULL) {
    printf("Failed to get IP.\n");
    return 1;
}
for (p = res; p != NULL; p = p->ai_next) {    // duyệt danh sách liên kết
    if (p->ai_family == AF_INET) {
        struct sockaddr_in addr;
        memcpy(&addr, p->ai_addr, p->ai_addrlen);
        printf("IP: %s\n", inet_ntoa(addr.sin_addr));
    }
}
freeaddrinfo(res);                            // trả lại bộ nhớ khi dùng xong
```

Lưu ý: `getaddrinfo` trả `0` là **thành công** (ngược với thói quen "0 là sai"). Truyền `NULL` cho tham số `hints` thì kết quả có thể lặp lại một IP nhiều lần (mỗi kiểu socket một lần).

## Lỗi hay gặp
- **Kết nối nhầm cổng** (vd. 8080 thành 36895). Quên `htons` khi gán `sin_port`.
- **Coi `255.255.255.255` là sai.** Chỉ kiểm tra `== INADDR_NONE` mà không so riêng xâu đó.
- **Rò rỉ bộ nhớ.** Quên `freeaddrinfo(res)`.
- **Hai IP in ra giống hệt nhau.** `inet_ntoa` trả về **cùng một bộ đệm tĩnh** mỗi lần gọi: `printf("%s %s", inet_ntoa(a), inet_ntoa(b))` in hai lần cùng một địa chỉ. Hãy `strcpy` kết quả ra mảng riêng trước khi gọi lần nữa (nhất là khi dùng nhiều luồng).
