# Kiểm tra và phân loại địa chỉ IPv4

Đọc từ stdin đến hết, mỗi dòng là một xâu (đã bỏ ký tự xuống dòng). Với mỗi dòng, gọi `inet_addr` như
code mẫu (`tcp_client.c`, `udp_sender.c`):

- Nếu `inet_addr` trả về `INADDR_NONE` **và** xâu **khác** `"255.255.255.255"`: in `INVALID`.
- Ngược lại in `VALID <địa chỉ chuẩn> <giá trị 32 bit dạng 0xXXXXXXXX theo thứ tự host> <LOẠI>`

`<địa chỉ chuẩn>` là kết quả của `inet_ntoa` (như `udp_receiver.c`). `<LOẠI>` xét theo thứ tự:

| Điều kiện | LOẠI |
|---|---|
| `127.0.0.0/8` | `LOOPBACK` |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | `PRIVATE` |
| `0.0.0.0` hoặc `255.255.255.255` | `SPECIAL` |
| còn lại | `PUBLIC` |

## Ràng buộc
- Mỗi dòng dài không quá 100 ký tự; dòng có thể kết thúc bằng `\r\n` (bỏ cả `\r`), dòng cuối có thể không có `\n`.
- Dòng trống cũng là một xâu (rỗng). Khoảng trắng **không** được cắt trước khi gọi `inet_addr`.
- Hex in hoa, đủ 8 chữ số (`0x08080808`). Input có tới 100 000 dòng.

## Ví dụ

```
192.168.1.1      →  VALID 192.168.1.1 0xC0A80101 PRIVATE
8.8.8.8          →  VALID 8.8.8.8 0x08080808 PUBLIC
255.255.255.255  →  VALID 255.255.255.255 0xFFFFFFFF SPECIAL
256.1.1.1        →  INVALID
10.1             →  VALID 10.0.0.1 0x0A000001 PRIVATE
```

## Gợi ý
- `inet_addr` trả về `s_addr` theo **thứ tự mạng**. Muốn in hex hay so sánh với mặt nạ
  (`(a & 0xFFF00000) == 0xAC100000`) thì phải `ntohl` trước.
- `inet_addr` dễ dãi hơn bạn nghĩ: nhận dạng viết tắt (`10.1` là `10.0.0.1`), số bát phân (`010` là 8), số hex
  (`0x7f`). Đừng tự kiểm tra xâu, cứ để `inet_addr` quyết định; `inet_ntoa` sẽ in lại dạng chuẩn.
- Giá trị lỗi `INADDR_NONE` trùng với địa chỉ hợp lệ `255.255.255.255`: đây là lý do người ta tạo ra các hàm mới
  hơn như `inet_pton`.
