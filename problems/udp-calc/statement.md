# Máy tính qua UDP

Viết server UDP `./server <cổng>`. Mỗi datagram là **một yêu cầu** (không có `\n`), server trả lời
người gửi bằng **một datagram**.

| Yêu cầu | Phản hồi |
|---|---|
| `<a> <op> <b>`, với `a`, `b` là số nguyên 64 bit có dấu, `op` ∈ `+ - * / %` | kết quả (số nguyên, `/` chia nguyên làm tròn về 0 như C) |
| chia hoặc lấy dư cho 0 | `ERROR div0` |
| `COUNT` | số phép tính **thành công** mà **người gửi này** đã thực hiện |
| mọi thứ khác (sai cú pháp, thừa hoặc thiếu thành phần, số không hợp lệ) | `ERROR syntax` |

Các thành phần cách nhau **đúng một dấu cách**. Người gửi xác định bằng cặp IP + cổng. Hỗ trợ ít nhất
100 người gửi.

## Ràng buộc và bộ chấm kiểm tra
- Số hợp lệ: `-` tùy chọn rồi một hoặc nhiều chữ số (`007`, `-0` hợp lệ); trong khoảng `int64`
  (`-9223372036854775808 … 9223372036854775807`), ngoài khoảng → `ERROR syntax`. Dấu `+`, `0x`, `1e3`, `1.5` → `ERROR syntax`.
- Đúng **một** dấu cách giữa các thành phần; thừa/thiếu dấu cách, tab, dấu cách đầu/cuối → `ERROR syntax`.
  `COUNT` phải khớp nguyên datagram.
- Datagram có thể dài tới vài KB (→ `ERROR syntax`). Tới 100 người gửi (cùng IP, khác cổng); bộ chấm so với mô hình
  trên hàng nghìn yêu cầu ngẫu nhiên.

## Ví dụ

```
"12 + 30"   →  "42"
"-7 / 2"    →  "-3"
"5 % 0"     →  "ERROR div0"
"5+3"       →  "ERROR syntax"
"COUNT"     →  "2"
```

## Gợi ý
Tự duyệt từng ký tự của số (`-` tùy chọn rồi chữ số) và cộng dồn giá trị, dừng với lỗi nếu sắp vượt
`9223372036854775807` (hoặc `...808` với số âm). Lấy địa chỉ người gửi từ `recvfrom` như `udp_receiver.c`. Giữ một bảng
`(địa chỉ, cổng) → bộ đếm` như bài *udp-boundary*. Kết quả tràn số không được kiểm tra trong test.
