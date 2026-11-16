# UDP echo server

Viết server **UDP** chạy bằng `./server <cổng>`. Với mỗi datagram nhận được, server gửi lại
**đúng datagram đó** (cùng nội dung, cùng độ dài) cho **đúng người gửi**.

- UDP không có kết nối: dùng `recvfrom` để biết địa chỉ người gửi, `sendto` để trả lời.
- Datagram dài tối đa 2048 byte, có thể chứa byte `0x00`.
- Datagram **rỗng** (0 byte) là hợp lệ: trả lời bằng một datagram rỗng. Với UDP, `recvfrom` trả về
  0 **không** có nghĩa là "đối phương đóng kết nối" như TCP.

## Ràng buộc và bộ chấm kiểm tra
- Datagram 0–2048 byte, có thể bắt đầu bằng / toàn là byte `0x00`; trả lời bằng **đúng số byte** nhận được.
- Tới 30 người gửi xen kẽ ngẫu nhiên; người gửi có thể biến mất trước khi nhận phản hồi. 200 datagram có thể đến
  dồn trước khi người gửi đọc.

## Ví dụ

```
client A gửi "ping"   →  A nhận "ping"
client B gửi "hello"  →  B nhận "hello" (A không nhận gì)
```
