# Phân giải tên miền

Đọc từ stdin đến hết, mỗi dòng là một tên miền (bỏ qua dòng trống). Dùng `getaddrinfo` với
`ai_family = AF_INET` và `ai_socktype = SOCK_STREAM` để phân giải, rồi in một dòng:

```
<tên>: <ip1> <ip2> ...
```

Các IP in theo **đúng thứ tự `getaddrinfo` trả về**. Nếu phân giải thất bại thì in `<tên>: NOT_FOUND`.
Nhớ `freeaddrinfo`.

## Ràng buộc
- Tên miền dài tối đa 253 ký tự; một tên có thể ứng với **nhiều** IP (tới 12) — in đủ tất cả.
- Tên chỉ có bản ghi IPv6 thì là `NOT_FOUND` (chỉ lấy IPv4). Tên in ra đúng như dòng đã đọc (giữ hoa/thường).
- Dòng có thể kết thúc bằng `\r\n`; dòng cuối có thể không có `\n`. Input có tới 1000 dòng.

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
