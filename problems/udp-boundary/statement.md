# Ranh giới datagram

Khác với TCP, UDP **giữ nguyên ranh giới thông điệp**: hai lần `sendto` luôn là hai lần `recvfrom`,
không bao giờ bị gộp hay cắt nhỏ.

Viết server UDP `./server <cổng>`. Với mỗi datagram nhận được, trả lời người gửi một datagram:

```
LEN <số byte> <số thứ tự>
```

trong đó `<số thứ tự>` là thứ tự của datagram này **trong số các datagram cùng người gửi**
(đếm từ 1; người gửi xác định bằng cặp IP + cổng).

- Datagram có thể dài tới **65507 byte** (giới hạn của UDP trên IPv4). Bộ đệm nhỏ sẽ làm
  `recvfrom` **cắt cụt** datagram mà không báo lỗi.
- Datagram rỗng là hợp lệ (`LEN 0 ...`).
- Hỗ trợ ít nhất 100 người gửi khác nhau.

## Ví dụ

```
A gửi "hello"            →  A nhận "LEN 5 1"
A gửi "abc"              →  A nhận "LEN 3 2"
B gửi 60000 byte         →  B nhận "LEN 60000 1"
```
