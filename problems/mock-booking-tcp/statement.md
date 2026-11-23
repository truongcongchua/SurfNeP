# Thi thử 1: Đặt chỗ qua TCP

> **Thời gian: 90 phút.** Chỉ các test mẫu hiển thị chi tiết; các test còn lại chỉ báo đúng/sai.

Viết server đặt ghế cho một buổi chiếu phim: `./server <cổng> <N> <S>`.
- `N` (1 ≤ N ≤ 50): số client **kết nối đồng thời** tối đa.
- `S` (1 ≤ S ≤ 100): số ghế, đánh số `1 … S`, ban đầu đều trống.

Được dùng bất kỳ kỹ thuật nào trong code mẫu: `select`, đa luồng (nhớ mutex), v.v.

## Kết nối
- Đang có ít hơn `N` client: gửi `WELCOME`. Ngược lại gửi `FULL` và đóng kết nối đó.
- Client rời đi (bằng `QUIT` hoặc đóng đột ngột) thì giải phóng chỗ, **nhưng ghế đã đặt vẫn giữ**.

## Lệnh (mỗi lệnh một dòng, bỏ `\r` cuối dòng; các thành phần cách nhau một dấu cách)

| Lệnh | Điều kiện | Phản hồi |
|---|---|---|
| `LOGIN <tên>` | tên không chứa dấu cách, dài ≤ 32 | `OK <tên>` (được đăng nhập lại để đổi tên) |
| `LIST` | | `FREE <k> <g1> <g2> …` (ghế trống tăng dần; `k = 0` thì chỉ `FREE 0`) |
| `BOOK <g>` | đã LOGIN | `BOOKED <g>` · `TAKEN <g>` nếu đã có người đặt · `INVALID` nếu `g` không phải số trong `1…S` |
| `CANCEL <g>` | đã LOGIN | `CANCELLED <g>` · `NOT_YOURS <g>` nếu ghế trống hoặc người khác đặt · `INVALID` |
| `MINE` | đã LOGIN | `MINE <k> <g1> …` (ghế của **tên** này, tăng dần) |
| `QUIT` | | `BYE` rồi đóng |
| lệnh BOOK/CANCEL/MINE khi chưa LOGIN | | `LOGIN_FIRST` |
| mọi thứ khác | | `ERROR` |

Quyền sở hữu ghế gắn với **tên**: client khác LOGIN cùng tên thì được hủy và xem ghế đó.

## Ví dụ (N = 2, S = 5)

```
A: (kết nối)            ← WELCOME
A: LIST                 ← FREE 5 1 2 3 4 5
A: BOOK 2               ← LOGIN_FIRST
A: LOGIN an             ← OK an
A: BOOK 2               ← BOOKED 2
B: (kết nối)            ← WELCOME
B: LOGIN binh           ← OK binh
B: BOOK 2               ← TAKEN 2
B: CANCEL 2             ← NOT_YOURS 2
C: (kết nối)            ← FULL
A: MINE                 ← MINE 1 2
```

## Ràng buộc (test ẩn kiểm tra đúng các điều này)
- Các thành phần cách nhau một dấu cách; dòng có thể kết thúc bằng `\r\n`; mỗi dòng tối đa 1000 byte.
- Tên dài 1–32 byte (33 trở lên → `ERROR`). Ghế hợp lệ là số thập phân `1…S` (không dấu, không chữ).
- Lệnh có thể bị cắt vụn từng byte, hoặc hàng trăm lệnh dính nhau trong một lần gửi.
- Nhiều client có thể **cùng lúc** tranh một ghế: mỗi ghế chỉ có đúng một chủ.
- Kết nối mới luôn ở trạng thái **chưa LOGIN**, kể cả khi dùng lại chỗ của client cũ.
- Client có thể mất kết nối đột ngột (RST); chương trình chạy với giới hạn 256 file
  descriptor, bộ chấm cho 300 kết nối vào-ra và 300 kết nối bị `FULL`.
