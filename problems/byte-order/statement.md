# Đổi thứ tự byte

Máy tính x86 lưu số nguyên theo **little-endian**, còn giao thức mạng dùng **big-endian**
(network byte order). Viết chương trình đọc từ stdin đến hết, mỗi dòng có dạng `u16 X` hoặc `u32 X`
(`X` là số thập phân không âm, vừa kiểu tương ứng).

Với mỗi dòng, in ra:
1. các byte của `X` **theo thứ tự mạng**, mỗi byte là 2 chữ số hex in hoa, cách nhau một dấu cách;
2. dấu ` | `;
3. giá trị thu được nếu **máy này** đọc nguyên dãy byte đó như một số nguyên của chính nó (thập phân).

Dòng không đúng định dạng (sai kiểu, thiếu số, thừa từ, số âm, số quá lớn) thì in `ERROR`.
Dòng trống thì bỏ qua, không in gì.

## Ví dụ

```
u16 4660          →  12 34 | 13330
u32 1             →  00 00 00 01 | 16777216
u16 70000         →  ERROR
```

## Gợi ý
Dùng `htons`/`htonl` rồi `memcpy` kết quả vào một mảng `unsigned char` để xem từng byte.
Phần 3 chính là giá trị trả về của `htons`/`htonl` trên máy little-endian. Đây là lỗi kinh điển khi
quên đổi byte order: gửi cổng 4660 nhưng phía kia đọc ra 13330.
