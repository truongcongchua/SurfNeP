---
title: "Thứ tự byte (byte order)"
chapter: 2
ref: "Lecture notes §2.2"
---

## Tóm tắt
- **Little-endian** (x86, ARM thường gặp): byte thấp nằm ở địa chỉ thấp. `0x12345678` lưu là `78 56 34 12`.
- **Big-endian** = **network byte order**: byte cao trước. `0x12345678` gửi đi là `12 34 56 78`.
- Mọi số nguyên nhiều byte đi qua mạng phải đổi sang network order.

| Hàm | Kích thước | Chiều |
|---|---|---|
| `htons` / `ntohs` | 16 bit (cổng) | host ↔ network |
| `htonl` / `ntohl` | 32 bit (IPv4, độ dài) | host ↔ network |

```c
uint16_t port_net = htons(9000);
uint32_t len_net  = htonl(1234);
// nhận về: uint32_t len = ntohl(len_net);
```

## Kiểm tra máy mình là endian nào
```c
uint16_t x = 1;
int little = *(uint8_t *)&x == 1;
```

## Bẫy thường gặp
- Đổi sai chiều: gửi `ntohl` thay vì `htonl` (trên máy little-endian cho kết quả sai, trên máy big-endian lại "đúng" nên khó phát hiện).
- Đổi **hai lần** một giá trị, hoặc quên đổi khi đọc lại từ socket.
- Dùng `htons` cho số 32 bit (bị cắt mất 16 bit cao).
- `ntohs(htons(x)) == x`: nếu kết quả bài toán đảo ngược khi chạy hai lần thì kiểm tra lại xem có đổi dư không.
- Chuỗi ký tự (từng byte) **không** cần đổi byte order.
