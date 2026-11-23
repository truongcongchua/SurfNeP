---
title: "Thông điệp có độ dài tiền tố & truyền struct"
chapter: 2
ref: "Lecture notes §2.3–2.5; lab10 (padding của struct)"
---

## Hiểu nhanh
TCP không cho biết một thông điệp dài bao nhiêu (xem thẻ *TCP là luồng byte*). Cách gọn nhất: **gửi độ dài trước, nội dung sau**, giống gói hàng có dán nhãn "bên trong có 25 món".

```
| 4 byte: độ dài N | N byte: nội dung |
```
Bên nhận đọc đủ 4 byte → biết N → đọc tiếp đủ N byte. Không cần ký tự kết thúc, nội dung chứa gì cũng được (kể cả `\n`, byte `0`).

## Code mẫu
```c
// ---- GỬI ----
unsigned int len = strlen(msg);
unsigned int len_net = htonl(len);   // độ dài là số 4 byte → đổi sang network order
send(fd, &len_net, 4, 0);            // socket blocking: send chờ tới khi gửi hết
send(fd, msg, len, 0);

// ---- NHẬN: lặp recv tới khi đủ 4 byte ----
unsigned int len_net;
int got = 0;
while (got < 4) {
    int k = recv(fd, (char *)&len_net + got, 4 - got, 0);
    if (k <= 0) { /* bên kia đã đóng */ break; }
    got += k;
}
unsigned int len = ntohl(len_net);   // đổi về số bình thường (kiểu không dấu!)
if (len > MAX_LEN) { /* quá lớn: từ chối, đừng tin bừa */ }

// ---- rồi lặp recv tới khi đủ len byte ----
char *buf = malloc(len + 1);
unsigned int have = 0;
while (have < len) {
    int k = recv(fd, buf + have, len - have, 0);
    if (k <= 0) break;
    have += k;
}
buf[len] = '\0';                     // thêm '\0' nếu muốn dùng như xâu
```
**Không** dùng `recv(fd, &len_net, 4, 0)` một lần như `tcp_server.c`: có thể chỉ nhận được 1-3 byte.

## Gửi cả một struct được không?
```c
struct SinhVien { char name[32]; int age; float gpa; };
send(fd, &sv, sizeof sv, 0);         // cách "nhanh", nhưng có 3 cái bẫy
```
1. **Byte đệm (padding).** Trình biên dịch có thể chèn byte trống giữa các trường để CPU đọc nhanh hơn. Hai bên biên dịch khác nhau (32/64 bit, khác cờ) thì `sizeof` khác nhau, đọc lệch hết.
2. **Thứ tự byte.** `age`, `gpa` là số nhiều byte, máy hai bên có thể khác endian (xem thẻ *Thứ tự byte*).
3. **Con trỏ.** Trường kiểu `char *` chỉ chứa **địa chỉ trong RAM máy gửi**, sang máy kia là vô nghĩa. Phải gửi nội dung xâu.

## Cách an toàn: gửi từng trường
Tự xếp từng trường vào một mảng byte (gọi là **tuần tự hoá** / serialization):
```c
unsigned char out[64];
size_t off = 0;

memcpy(out + off, sv.name, 32);               off += 32;   // xâu: copy nguyên 32 byte
unsigned int age_net = htonl(sv.age);
memcpy(out + off, &age_net, 4);               off += 4;    // số: đổi byte order rồi copy

send(fd, out, off, 0);
```
Bên nhận làm ngược lại đúng thứ tự đó (`memcpy` ra rồi `ntohl`).

Cách khác dễ debug hơn: gửi dạng văn bản, vd. `"An|20|3.5\n"`, bên nhận tách bằng `sscanf`/`strtok`.

## Lỗi hay gặp
- **Bên nhận đọc ra số khổng lồ.** Quên `htonl`/`ntohl` cho độ dài, hoặc đọc chưa đủ 4 byte.
- **Các trường sau bị lệch.** `sizeof(struct)` hai bên khác nhau do padding. Sửa: gửi từng trường.
- **Chương trình cấp phát hết bộ nhớ / crash.** Tin độ dài đối phương gửi mà không kiểm tra giới hạn.
- **Xâu thừa/thiếu một ký tự.** Hai bên không thống nhất có gửi kèm `'\0'` hay không. Phải quy ước rõ.
