# Phân giải tên miền

Đọc từ stdin đến hết, mỗi dòng là một tên miền (bỏ qua dòng trống). Dùng `getaddrinfo` với
`ai_family = AF_INET` và `ai_socktype = SOCK_STREAM` để phân giải, rồi in một dòng:

```
<tên>: <ip1> <ip2> ...
```

Các IP in theo **đúng thứ tự `getaddrinfo` trả về**. Nếu phân giải thất bại thì in `<tên>: NOT_FOUND`.
Nhớ `freeaddrinfo`.

## Ví dụ

```
may.soict.test   →  may.soict.test: 10.0.0.5
khong.ton.tai    →  khong.ton.tai: NOT_FOUND
```

> Bộ chấm chạy **không có Internet**. Các tên miền trong test được khai báo sẵn trong `/etc/hosts`
> của máy chấm (ví dụ `may.soict.test`). Đừng in thêm dòng "IPv4"/"IP:" như code mẫu trên lớp.

## Gợi ý
Code mẫu `domain2ip.c` trên lớp đã có gần đủ. Hãy đặt `hints` để chỉ lấy IPv4 và mỗi địa chỉ chỉ
xuất hiện một lần (vì sao `SOCK_STREAM` giúp được việc này?).
