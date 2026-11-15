# Thi thử 2: Quiz server UDP

> **Thời gian: 90 phút.** Chỉ các test mẫu hiển thị chi tiết; các test còn lại chỉ báo đúng/sai.

Viết server trắc nghiệm qua **UDP**: `./server <cổng> <tệp câu hỏi> <N>`.
- Tệp câu hỏi: mỗi dòng `<câu hỏi>|<A>|<B>|<C>|<D>|<đáp án đúng: A, B, C hoặc D>`, tối đa 100 dòng.
  Dòng trống thì bỏ qua.
- Tối đa `N` người chơi (1 ≤ N ≤ 100) tham gia cùng lúc. Người chơi xác định bằng **cặp IP + cổng**
  của datagram.

Mỗi datagram là một yêu cầu (không có `\n`); server trả lời người gửi **đúng một datagram**.

| Yêu cầu | Phản hồi |
|---|---|
| `JOIN <tên>` (tên không chứa dấu cách, ≤ 32 ký tự) | `WELCOME <tên> <số câu hỏi>` · `FULL` nếu đã đủ N người · `ALREADY` nếu địa chỉ này đã tham gia |
| `Q <i>` | `Q <i> <câu hỏi>\|<A>\|<B>\|<C>\|<D>` (đúng dòng trong tệp, bỏ phần đáp án) · `INVALID` nếu `i` ngoài `1…số câu` |
| `ANS <i> <X>` (X ∈ `A B C D`) | `CORRECT` · `WRONG` · `ANSWERED` nếu đã trả lời câu `i` · `INVALID` nếu `i` hoặc `X` sai |
| `SCORE` | `SCORE <số câu đúng> <số câu đã trả lời>` |
| `TOP` | `TOP <tên1>:<điểm1> <tên2>:<điểm2> …`: tối đa 3 người đang chơi, điểm giảm dần, cùng điểm thì tên tăng dần |
| `LEAVE` | `BYE`, giải phóng chỗ, xoá điểm |
| `Q`/`ANS`/`SCORE`/`TOP`/`LEAVE` khi chưa JOIN | `JOIN_FIRST` |
| mọi thứ khác | `ERROR` |

`Q <i>` không cần đã trả lời câu trước. Mỗi câu chỉ được trả lời một lần, lần đầu là lần được tính.

## Ví dụ (N = 3)

```
A: JOIN an        → WELCOME an 5
A: Q 2            → Q 2 Hàm nào chuyển cổng sang thứ tự mạng?|ntohs|htonl|htons|inet_pton
A: ANS 2 C        → CORRECT
A: ANS 2 A        → ANSWERED
A: SCORE          → SCORE 1 1
B: SCORE          → JOIN_FIRST
```
