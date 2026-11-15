# Key-Value server tối đa N client

> Dạng đề giữa kỳ: *"Tạo ứng dụng server/client dùng TCP phục vụ một bài toán với số lượng tối đa N client."*

Viết server chạy bằng `./server <cổng> <N>`. Server lưu một bảng **key → value dùng chung**
cho mọi client và phục vụ **đồng thời** tối đa `N` client (1 ≤ N ≤ 50). Được chọn kỹ thuật
`select()`/`poll()` hoặc đa luồng. Đa tiến trình (`fork`) không phù hợp vì dữ liệu phải dùng chung.

## Kết nối
- Khi có client mới mà số client đang kết nối **nhỏ hơn N**: gửi `WELCOME`.
- Nếu đã đủ `N` client: gửi `FULL` rồi đóng kết nối đó ngay.
- Client ngắt kết nối (bằng `QUIT` hoặc đóng đột ngột) thì giải phóng một chỗ.

## Lệnh

Mỗi lệnh là một dòng kết thúc bằng `\n` (bỏ qua `\r` cuối dòng). Key và value là các xâu
không chứa dấu cách, độ dài không quá 64 ký tự. Bảng chứa tối đa 1000 key.

| Lệnh | Phản hồi |
|---|---|
| `SET <key> <value>` | `OK` (ghi đè nếu key đã có) |
| `GET <key>` | `VALUE <value>` hoặc `NOT_FOUND` |
| `DEL <key>` | `OK` hoặc `NOT_FOUND` |
| `COUNT` | `COUNT <số key hiện có>` |
| `QUIT` | `BYE` rồi đóng kết nối |
| Mọi thứ khác (sai tên lệnh, thiếu hoặc thừa tham số) | `ERROR` |

## Ví dụ (N = 2)

```
C1 kết nối        → WELCOME
C1: SET mssv 2021  → OK
C2 kết nối        → WELCOME
C2: GET mssv       → VALUE 2021
C3 kết nối        → FULL (bị đóng)
C1: QUIT           → BYE
C3 kết nối lại    → WELCOME
```

## Bộ chấm kiểm tra
- Đúng giao thức, kể cả lệnh bị cắt vụn hoặc nhiều lệnh dính nhau trong một lần gửi.
- Một client im lặng không được làm chậm client khác.
- Giới hạn `N` chính xác, và chỗ được giải phóng khi client rời đi.
