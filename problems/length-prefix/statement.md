# Thông điệp có độ dài tiền tố

Giao thức theo dòng không truyền được dữ liệu nhị phân có chứa `'\n'`. Cách phổ biến hơn là gửi
**độ dài trước, dữ liệu sau**.

Viết server `./server <cổng>` (phục vụ lần lượt từng client là đủ). Mỗi thông điệp gồm:

```
+----------------------+------------------+
| L: 4 byte, big-endian | L byte dữ liệu   |
+----------------------+------------------+
```

với `0 ≤ L ≤ 65536`. Với mỗi thông điệp nhận được, server gửi lại **một thông điệp cùng định dạng**,
trong đó dữ liệu được đổi chữ cái ASCII thường `a`–`z` thành chữ hoa, các byte khác giữ nguyên.

Nếu `L > 65536`, server **đóng kết nối** với client đó ngay (không trả lời) và phục vụ client tiếp theo.

## Ví dụ

```
client gửi: 00 00 00 05 'h' 'e' 'l' 'l' 'o'
server gửi: 00 00 00 05 'H' 'E' 'L' 'L' 'O'
```

## Bộ chấm kiểm tra
- Phần độ dài 4 byte có thể đến **từng byte một**; ranh giới các lần gửi rơi vào bất kỳ đâu.
- Tới 1000 thông điệp có thể **dính nhau** trong một lần gửi; client có thể gửi dồn tới khi đầy bộ đệm rồi mới đọc.
- Thông điệp rỗng (`L = 0`), mọi kích thước quanh ranh giới bộ đệm, và lớn nhất 65536 byte chứa dữ liệu nhị phân
  (đủ 256 giá trị byte; chỉ `a`–`z` được đổi).
- `L` là số **không dấu** 32 bit: `L = 65537`, `0x80000000`, `0xFFFFFFFF` đều phải đóng kết nối (đừng đọc vào `int`).
- Client có thể đóng giữa chừng (thiếu header hoặc thiếu dữ liệu) hoặc ngừng gửi (`shutdown`) rồi chờ đọc.
  Chương trình chạy với giới hạn 256 file descriptor; bộ chấm cho 300 client lần lượt.

## Gợi ý
Khác `tcp_server.c` (gọi `recv` một lần): một lần `recv` có thể trả về **ít hơn** số byte bạn xin. Hãy gọi
`recv` trong vòng lặp, cộng dồn số byte đã nhận, tới khi đủ 4 byte độ dài; `ntohl` ra `L` (kiểu
`unsigned int`), rồi lại lặp `recv` tới khi đủ `L` byte. `send` trên socket blocking tự chờ gửi hết nên
gọi một lần là đủ.
