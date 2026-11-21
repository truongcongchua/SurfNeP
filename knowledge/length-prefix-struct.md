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
uint32_t len = strlen(msg);
uint32_t len_net = htonl(len);       // độ dài là số 4 byte → đổi sang network order
send_all(fd, &len_net, 4);
send_all(fd, msg, len);

// ---- NHẬN ----
uint32_t len_net;
if (recv_all(fd, &len_net, 4) < 0) { /* bên kia đã đóng */ }
uint32_t len = ntohl(len_net);       // đổi về số bình thường
if (len > MAX_LEN) { /* quá lớn: từ chối, đừng tin bừa */ }
char *buf = malloc(len + 1);
recv_all(fd, buf, len);
buf[len] = '\0';                     // thêm '\0' nếu muốn dùng như xâu
```
`send_all`/`recv_all` xem ở thẻ *Vòng đời socket TCP* và *TCP là luồng byte*. **Không** dùng `recv(fd, &len_net, 4, 0)` một lần: có thể chỉ nhận được 1-3 byte.

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
uint32_t age_net = htonl((uint32_t)sv.age);
memcpy(out + off, &age_net, 4);               off += 4;    // số: đổi byte order rồi copy

send_all(fd, out, off);
```
Bên nhận làm ngược lại đúng thứ tự đó (`memcpy` ra rồi `ntohl`).

Cách khác dễ debug hơn: gửi dạng văn bản, vd. `"An|20|3.5\n"`, bên nhận tách bằng `sscanf`/`strtok`.

## Lỗi hay gặp
- **Bên nhận đọc ra số khổng lồ.** Quên `htonl`/`ntohl` cho độ dài, hoặc đọc chưa đủ 4 byte.
- **Các trường sau bị lệch.** `sizeof(struct)` hai bên khác nhau do padding. Sửa: gửi từng trường.
- **Chương trình cấp phát hết bộ nhớ / crash.** Tin độ dài đối phương gửi mà không kiểm tra giới hạn.
- **Xâu thừa/thiếu một ký tự.** Hai bên không thống nhất có gửi kèm `'\0'` hay không. Phải quy ước rõ.
