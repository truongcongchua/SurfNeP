# Echo server tối đa N client

> Bước đệm trước dạng đề giữa kỳ: *"server TCP phục vụ tối đa N client"*. Giao thức cố tình đơn giản
> để bạn chỉ tập trung vào **đếm client và giải phóng chỗ**. Bài *kv-max-n* sẽ thêm trạng thái dùng chung.

Viết server chạy bằng `./server <cổng> <N>` (1 ≤ N ≤ 50). Phục vụ **đồng thời** tối đa `N` client,
dùng `select()`/`poll()` hoặc đa luồng (không dùng `fork`).

## Kết nối
- Client mới khi số client đang kết nối **nhỏ hơn N**: gửi `WELCOME`.
- Đã đủ `N` client: gửi `FULL` rồi đóng kết nối đó ngay (không tính vào N).
- Client rời đi (gửi `QUIT` hoặc đóng đột ngột) thì giải phóng một chỗ.

## Lệnh (mỗi lệnh là một dòng kết thúc bằng `\n`, bỏ `\r` cuối dòng)

| Lệnh | Phản hồi |
|---|---|
| `COUNT` | `COUNT <số client đang kết nối, tính cả bạn>` |
| `QUIT` | `BYE` rồi đóng kết nối |
| dòng khác (kể cả dòng rỗng) | `ECHO <dòng đó>` |

## Ví dụ (N = 2)

```
C1 kết nối       → WELCOME
C1: hello        → ECHO hello
C2 kết nối       → WELCOME
C2: COUNT        → COUNT 2
C3 kết nối       → FULL (bị đóng)
C1: QUIT         → BYE
C3 kết nối lại   → WELCOME
```

## Ràng buộc và bộ chấm kiểm tra
- Mỗi dòng dài tối đa 1000 byte (không tính `\n`), không chứa byte `0x00`. Lệnh phân biệt hoa thường và phải khớp
  **nguyên dòng**: `COUNT ` (thừa dấu cách) hay `count` là dòng thường → `ECHO ...`.
- Dòng có thể bị cắt thành mảnh 1 byte, hoặc tới 1000 dòng dính nhau trong một lần gửi. Nếu `QUIT` nằm giữa
  khối, xử lý các dòng trước nó, gửi `BYE`, đóng và bỏ phần còn lại.
- `N` từ 1 tới 50. Client bị `FULL` phải được **đóng ngay** và không chiếm chỗ. Chỗ được trả lại khi client
  `QUIT`, đóng thường, hay mất kết nối đột ngột (RST).
- Chạy với giới hạn **256 file descriptor**: bộ chấm cho 300 client lần lượt vào-ra và 300 kết nối liên tiếp bị
  `FULL`. Client dồn lệnh rồi RST không được làm server chết (`SIGPIPE`).

## Bẫy hay gặp
- `>` và `>=` khi so sánh với `N` (lệch một client).
- Quên giảm bộ đếm khi client **đóng đột ngột** (`recv` trả `0` hoặc `-1`), chứ không chỉ khi nhận `QUIT`.
- Dòng bị cắt vụn qua nhiều lần `recv`, hoặc nhiều dòng dính nhau trong một lần `recv`.
