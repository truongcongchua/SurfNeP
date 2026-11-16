---
title: "TCP là luồng byte (ghép dòng, phân mảnh)"
chapter: 2
ref: "Lecture notes §2.3 — recv() và ranh giới thông điệp"
---

## Tóm tắt
TCP **không có ranh giới thông điệp**. Một lần `send(100 byte)` có thể đến nơi thành 3 lần `recv`, hoặc 3 lần `send` có thể gộp thành 1 lần `recv`. Giao thức tầng ứng dụng phải tự cho biết "thông điệp kết thúc ở đâu".

## Ba cách đóng khung (framing)
1. **Ký tự kết thúc** (vd. `\n`, `\r\n\r\n` của HTTP): đọc đến khi gặp.
2. **Độ dài cố định**: luôn đọc đúng K byte.
3. **Độ dài tiền tố**: gửi số byte trước, rồi đến nội dung (xem thẻ *Thông điệp có độ dài & struct*).

## Mẫu: đọc từng dòng
```c
char buf[4096]; size_t len = 0;           // len = số byte đang giữ trong buf
for (;;) {
    ssize_t n = recv(fd, buf + len, sizeof buf - len, 0);
    if (n <= 0) break;                    // đóng hoặc lỗi
    len += n;
    char *nl;
    while ((nl = memchr(buf, '\n', len)) != NULL) {
        size_t linelen = nl - buf + 1;
        /* xử lý buf[0 .. linelen) */
        memmove(buf, buf + linelen, len - linelen);   // giữ lại phần dư cho lần sau
        len -= linelen;
    }
}
```

## Mẫu: đọc đủ n byte
```c
int recv_all(int fd, void *p, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t r = recv(fd, (char *)p + got, n - got, 0);
        if (r <= 0) return -1;
        got += r;
    }
    return 0;
}
```

## Chuỗi đánh dấu bị cắt đôi
Tìm chuỗi dừng (vd. `"bye"`) bằng cách tìm **trong bộ đệm tích luỹ**, không tìm trong từng lần `recv`: chuỗi có thể nằm vắt qua hai lần nhận (`"by"` + `"e"`).

## Bẫy thường gặp
- Giả sử một `recv` = một lệnh. Test cục bộ vẫn chạy vì dữ liệu nhỏ, nhưng test ẩn cố tình chia nhỏ từng byte.
- Coi bộ đệm như xâu C mà quên thêm `'\0'` trước khi dùng `strstr`/`printf`.
- Làm mất phần dư sau dấu `\n` (client gửi hai lệnh trong một segment).
- Quên xử lý `\r\n` (telnet/HTTP) chỉ cắt ở `\n`.
- Vòng đệm đầy mà chưa gặp ký tự kết thúc → phải có giới hạn, không `recv` vào kích thước 0.
