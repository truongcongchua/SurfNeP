# Kiểm tra và phân loại địa chỉ IPv4

Đọc từ stdin đến hết, mỗi dòng là một xâu (đã bỏ ký tự xuống dòng). Với mỗi dòng:

- Nếu `inet_pton(AF_INET, ...)` **chấp nhận** xâu: in
  `VALID <địa chỉ chuẩn> <giá trị 32 bit dạng 0xXXXXXXXX theo thứ tự host> <LOẠI>`
- Ngược lại in `INVALID`.

`<địa chỉ chuẩn>` là kết quả của `inet_ntop`. `<LOẠI>` xét theo thứ tự:

| Điều kiện | LOẠI |
|---|---|
| `127.0.0.0/8` | `LOOPBACK` |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | `PRIVATE` |
| `0.0.0.0` hoặc `255.255.255.255` | `SPECIAL` |
| còn lại | `PUBLIC` |

## Ví dụ

```
192.168.1.1     →  VALID 192.168.1.1 0xC0A80101 PRIVATE
8.8.8.8         →  VALID 8.8.8.8 0x08080808 PUBLIC
256.1.1.1       →  INVALID
```

## Gợi ý
`inet_pton` cho `struct in_addr` có `s_addr` theo **thứ tự mạng**. Muốn so sánh với mặt nạ
(`addr & 0xFFF00000) == 0xAC100000`) thì phải `ntohl` trước. Lưu ý `inet_pton` khắt khe hơn
`inet_addr`: không nhận số 0 đứng đầu như `01.2.3.4`, cũng không nhận dạng viết tắt `10.1`.
