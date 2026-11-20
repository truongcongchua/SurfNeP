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

## Ràng buộc
- Các từ cách nhau bởi **một hoặc nhiều dấu cách** (dấu cách thừa ở đầu/cuối dòng được bỏ qua). Tab **không**
  phải dấu phân cách. Lệnh phân biệt hoa thường.
- Key/value dài 1–64 ký tự; có từ nào (sau tên lệnh) dài hơn 64 → `ERROR`. Mỗi dòng tối đa 1000 byte, không có `0x00`.
- Đã có 1000 key mà `SET` một key **mới** → `ERROR` (ghi đè key cũ vẫn `OK`).
- `N` từ 1 tới 50; chương trình chạy với giới hạn 256 file descriptor.

## Bộ chấm kiểm tra
- Đúng giao thức, kể cả lệnh bị cắt vụn (mảnh 1 byte) hoặc hàng trăm lệnh dính nhau trong một lần gửi.
- So sánh với **mô hình chuẩn** trên hàng nghìn lệnh ngẫu nhiên, nhiều client xen kẽ trên cùng một bảng.
- Một client im lặng / gửi dở lệnh không được làm chậm client khác.
- Giới hạn `N` chính xác (N=1, N=50), kết nối bị `FULL` được đóng ngay, chỗ được giải phóng khi client `QUIT`,
  đóng thường hoặc RST; 300 lượt vào-ra và 300 lần bị `FULL` không được làm rò rỉ fd.
- Client dồn lệnh rồi đóng đột ngột không được làm server chết (`SIGPIPE`).
