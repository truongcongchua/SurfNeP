---
title: "Thứ tự byte (byte order)"
chapter: 2
ref: "Lecture notes §2.2"
---

## Hiểu nhanh
Một số `int` 4 byte, ví dụ `0x12345678`, được cất trong bộ nhớ thành 4 ô. Nhưng **ô nào cất trước** thì mỗi loại máy một kiểu, giống như người viết ngày `21/11` còn người khác viết `11/21`:

| Kiểu | Cách cất `0x12345678` | Ai dùng |
|---|---|---|
| **Little-endian** | `78 56 34 12` (byte nhỏ trước) | hầu hết máy tính hiện nay (Intel/AMD, ARM) |
| **Big-endian** | `12 34 56 78` (byte lớn trước) | **mạng** quy ước dùng kiểu này |

Kiểu dùng trên mạng gọi là **network byte order** (= big-endian). Kiểu của máy bạn gọi là **host byte order**. Hai máy khác kiểu vẫn hiểu nhau vì cả hai đều đổi sang network order trước khi gửi.

**Quy tắc:** mọi số nguyên **từ 2 byte trở lên** đi qua mạng: đổi sang network order trước khi gửi, đổi về host order sau khi nhận.

## Bốn hàm đổi
Đọc tên hàm như một câu: `h` = host, `n` = network, `s` = short (16 bit), `l` = long (32 bit).

| Hàm | Đọc là | Dùng cho |
|---|---|---|
| `htons(x)` | **h**ost **to** **n**etwork **s**hort | cổng, số 16 bit, **trước khi gửi** |
| `ntohs(x)` | network to host short | số 16 bit, **sau khi nhận** |
| `htonl(x)` | host to network long | IP, độ dài, số 32 bit, **trước khi gửi** |
| `ntohl(x)` | network to host long | số 32 bit, **sau khi nhận** |

```c
#include <stdint.h>
#include <arpa/inet.h>

uint16_t port_net = htons(9000);     // gán vào sin_port
uint32_t len_net  = htonl(1234);     // gửi đi
// bên nhận:
uint32_t len = ntohl(len_net);       // 1234
```

Dùng kiểu có kích thước cố định `uint16_t`, `uint32_t` (trong `<stdint.h>`) thay cho `int`/`short` để chắc chắn số byte.

## Xem máy mình là kiểu nào
```c
uint16_t x = 1;
int little = (*(uint8_t *)&x == 1);  // byte đầu tiên là 1 → little-endian
```

## Xem từng byte của một số
```c
uint32_t v = htonl(0x12345678);
uint8_t *b = (uint8_t *)&v;
printf("%02x %02x %02x %02x\n", b[0], b[1], b[2], b[3]);   // 12 34 56 78
```

## Lỗi hay gặp
- **Đổi sai chiều** (dùng `ntohl` khi gửi). Trên máy little-endian hai hàm cho cùng kết quả nên vẫn "chạy", nhưng đọc code sẽ khó hiểu. Gửi dùng `hton*`, nhận dùng `ntoh*`.
- **Đổi hai lần** một giá trị → quay về giá trị ban đầu, coi như không đổi. Kiểm tra mỗi giá trị chỉ đổi **một lần** trên mỗi chiều.
- **Dùng `htons` cho số 32 bit** → mất 2 byte cao (vd. 70000 bị cắt còn 4464 trước khi đổi).
- **Đổi byte order cho xâu ký tự.** Không cần: mỗi ký tự chỉ 1 byte, không có chuyện thứ tự.
