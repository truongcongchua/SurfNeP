# Chuỗi dừng bị phân mảnh

Viết chương trình **server TCP** chạy bằng lệnh:

```
./server <cổng>
```

Server lắng nghe trên `<cổng>`, chấp nhận **đúng một** client rồi nhận dữ liệu từ client đó.

- Ngay khi dữ liệu đã nhận (tính từ đầu kết nối) **chứa chuỗi** `Ky thuat May tinh`,
  server gửi lại đúng một dòng `BYE\n`, đóng kết nối và kết thúc chương trình với mã 0.
- Trước thời điểm đó, server **không được gửi** gì cho client.
- Nếu client đóng kết nối mà chưa từng gửi đủ chuỗi trên, server đóng socket và kết thúc,
  **không** gửi `BYE`.

## Vì sao bài này khó hơn vẻ ngoài

TCP là giao thức **hướng luồng byte**: một lệnh `send()` bên client không tương ứng với một
lệnh `recv()` bên server. Chuỗi `Ky thuat May tinh` có thể đến thành nhiều mảnh
(`"Ky th"` rồi `"uat May tinh"`), hoặc dính liền với dữ liệu khác. Lời giải chỉ gọi
`strstr()` trên từng mảnh vừa nhận sẽ trượt.

## Ràng buộc và bộ chấm kiểm tra
- Chuỗi dừng có thể bị cắt ở **bất kỳ vị trí nào**, đến từng byte, hoặc nằm sau tới 2 MB dữ liệu khác.
- Dữ liệu là byte bất kỳ (có thể chứa `0x00`); so khớp **phân biệt hoa thường**, đúng từng byte.
- Dữ liệu có thể chứa nhiều **tiền tố chồng lấn** như `Ky thuat Ky thuat May tinh` — vẫn phải nhận ra.
- Client có thể đóng (FIN hoặc RST) mà chưa gửi đủ chuỗi: server đóng socket và kết thúc bình thường.

## Ví dụ

| Client gửi (mỗi dòng là một lần `send`) | Server phản hồi |
|---|---|
| `Ky thuat May tinh` | `BYE` rồi đóng |
| `Ky th` · `uat May` · ` tinh` | `BYE` rồi đóng |
| `xin chao` · `Ky thuat May` · *(đóng kết nối)* | *(không gửi gì)* |

## Kiến thức nền
- Lecture notes §2.3 — vòng đời `socket → bind → listen → accept → recv`.
- Lecture notes §2.4 — so sánh TCP (luồng) với UDP (thông điệp).
- Gợi ý: luôn kiểm tra giá trị trả về của `recv()`: `> 0`, `== 0` (đối phương đóng), `< 0` (lỗi).
