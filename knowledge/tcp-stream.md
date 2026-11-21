---
title: "TCP là luồng byte (ghép dòng, phân mảnh)"
chapter: 2
ref: "Lecture notes §2.3 — recv() và ranh giới thông điệp"
---

## Hiểu nhanh
TCP giống **nước chảy qua ống**, không phải **những gói hàng**. Bên gửi đổ vào 3 cốc nước, bên nhận có thể hứng được 1 xô, hoặc 5 cái chén. Tổng lượng nước thì đúng, nhưng **chỗ ngắt giữa các cốc đã mất**.

Cụ thể:
- `send("HELLO\n")` một lần, bên kia có thể `recv` ra `"HEL"` rồi lần sau `"LO\n"`.
- `send("A\n")` rồi `send("B\n")`, bên kia có thể `recv` một lần ra `"A\nB\n"`.

Chạy thử trên máy mình thường **không** thấy hiện tượng này vì dữ liệu nhỏ và nhanh, nhưng bộ chấm cố tình gửi từng mảnh nhỏ. Vì vậy chương trình **phải tự biết** một thông điệp kết thúc ở đâu.

## Ba cách đánh dấu chỗ kết thúc
1. **Ký tự kết thúc:** mỗi thông điệp kết thúc bằng `\n` (hoặc `\r\n\r\n` như HTTP). Đọc đến khi gặp ký tự đó.
2. **Độ dài cố định:** thông điệp nào cũng đúng K byte. Đọc đủ K byte.
3. **Gửi độ dài trước:** gửi 4 byte cho biết nội dung dài bao nhiêu, rồi mới gửi nội dung (xem thẻ *Thông điệp có độ dài & struct*).

## Mẫu 1: đọc từng dòng (cách 1)
Ý tưởng: dồn mọi thứ nhận được vào **một bộ đệm**, mỗi khi trong bộ đệm có `\n` thì cắt ra một dòng, phần còn lại giữ cho lần sau.
```c
char buf[4096];
size_t len = 0;                                     // số byte đang có trong buf

for (;;) {
    ssize_t n = recv(fd, buf + len, sizeof buf - len, 0);   // nhận NỐI TIẾP vào cuối
    if (n <= 0) break;                              // client đóng hoặc lỗi
    len += n;

    char *nl;
    while ((nl = memchr(buf, '\n', len)) != NULL) { // còn dòng hoàn chỉnh nào không?
        size_t linelen = nl - buf + 1;              // độ dài dòng, tính cả '\n'

        *nl = '\0';                                 // biến dòng thành xâu C
        if (nl > buf && nl[-1] == '\r') nl[-1] = '\0';   // bỏ '\r' nếu client gửi "\r\n"
        printf("Dong nhan duoc: %s\n", buf);        // ---- xử lý một dòng ở đây ----

        memmove(buf, buf + linelen, len - linelen); // dời phần còn lại lên đầu
        len -= linelen;
    }
    if (len == sizeof buf) break;                   // dòng quá dài, đệm đầy: tự xử lý tuỳ đề
}
```

## Mẫu 2: đọc đủ đúng n byte (cách 2 và 3)
`recv(fd, p, n, 0)` chỉ hứa trả **tối đa** n byte. Muốn đủ n byte thì lặp:
```c
int recv_all(int fd, void *p, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t r = recv(fd, (char *)p + got, n - got, 0);
        if (r <= 0) return -1;      // bên kia đóng giữa chừng hoặc lỗi
        got += r;
    }
    return 0;                       // đã đủ n byte
}
```
Gửi thì dùng `send_all` (xem thẻ *Vòng đời socket TCP*).

## Tìm một chữ đặc biệt (vd. `"bye"`)
Tìm trong **bộ đệm đã dồn**, đừng tìm trong từng lần `recv`: chữ đó có thể bị cắt đôi, lần này nhận `"by"`, lần sau nhận `"e"`.

## Lỗi hay gặp
- **Chạy máy mình đúng, nộp lên sai.** Giả định "một lần `recv` = một lệnh". Sửa: dùng Mẫu 1 hoặc Mẫu 2.
- **Lệnh thứ hai bị mất.** Client gửi `"A\nB\n"` cùng lúc, chương trình chỉ xử lý dòng đầu rồi xoá cả bộ đệm. Sửa: dùng vòng `while` cắt **hết** các dòng, giữ phần dư.
- **In ra rác hoặc `strstr` chạy lung tung.** Dữ liệu `recv` **không** có `'\0'` cuối. Phải tự thêm trước khi dùng như xâu.
- **So sánh `"QUIT"` luôn sai.** Client (telnet) gửi `"QUIT\r\n"`, bạn chỉ cắt `\n` nên còn `\r`. Sửa: bỏ cả `\r`.
- **Vòng lặp vô hạn.** Bộ đệm đầy (`len == sizeof buf`) mà chưa thấy `\n`, `recv` với kích thước 0 trả 0 mãi. Phải xử lý trường hợp đệm đầy.
