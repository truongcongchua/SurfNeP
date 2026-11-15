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

## Ví dụ

```
"12 + 30"   →  "42"
"-7 / 2"    →  "-3"
"5 % 0"     →  "ERROR div0"
"5+3"       →  "ERROR syntax"
"COUNT"     →  "2"
```

## Gợi ý
`strtoll` kèm kiểm tra `endptr` và `errno == ERANGE` để phát hiện số không hợp lệ. Giữ một bảng
`(địa chỉ, cổng) → bộ đếm` như bài *udp-boundary*. Kết quả tràn số không được kiểm tra trong test.
