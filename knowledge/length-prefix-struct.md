---
title: "Thông điệp có độ dài tiền tố & truyền struct"
chapter: 2
ref: "Lecture notes §2.3–2.5; lab10 (padding của struct)"
---

## Độ dài tiền tố
Mỗi thông điệp = **4 byte độ dài** (network order) + **nội dung**.

```c
// gửi
uint32_t n = htonl(len);
send_all(fd, &n, 4);
send_all(fd, data, len);

// nhận
uint32_t n;
recv_all(fd, &n, 4);          // phải đọc ĐỦ 4 byte, có thể bị chia
len = ntohl(n);
if (len > MAX) { /* từ chối, tránh cấp phát khổng lồ */ }
recv_all(fd, buf, len);
```

Điểm hay sai: `recv(fd, &n, 4, 0)` **không** đảm bảo đủ 4 byte → dùng `recv_all`.

## Gửi struct trực tiếp: có 3 vấn đề
```c
struct SV { char name[32]; int age; float gpa; };
send(fd, &sv, sizeof sv, 0);       // cách "ngây thơ"
```
1. **Padding:** trình biên dịch chèn byte đệm để căn lề; `sizeof` hai bên phải giống nhau (cùng biên dịch, cùng kiến trúc). Có thể dùng `__attribute__((packed))` nhưng truy cập chậm hơn/không an toàn.
2. **Byte order:** `int`/`float` nhiều byte → phải `htonl`/`ntohl` từng trường.
3. **Con trỏ:** struct chứa con trỏ thì gửi **địa chỉ**, vô nghĩa ở máy kia. Phải gửi nội dung.

## Cách an toàn: tuần tự hoá (serialization) từng trường
```c
uint32_t age_net = htonl(sv.age);
memcpy(buf + off, &age_net, 4); off += 4;
```
Hoặc gửi dạng văn bản (`"name|age|gpa\n"`) cho dễ debug, đổi lại tốn băng thông.

## Bẫy thường gặp
- `sizeof(struct)` khác nhau giữa client và server (khác cờ biên dịch / hệ 32-64 bit).
- Quên đổi byte order của một trường (đặc biệt `short`).
- Tin độ dài do đối phương gửi mà không giới hạn → tràn bộ đệm.
- Với xâu: gửi cả `'\0'` hay không phải **thống nhất** trong giao thức.
