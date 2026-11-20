# UDP client gửi từng dòng và đợi phản hồi

Phía **client** của các bài UDP: mỗi dòng nhập vào là một **datagram** gửi cho server, rồi đợi server trả lời.
Bạn có thể kiểm tra chéo bằng server do chính bạn viết ở bài *udp-echo* và *udp-calc*.

```
./udp_client <địa chỉ IP> <cổng>
```

## Yêu cầu
Lặp lại cho **từng dòng** đọc được từ stdin:

1. Gửi nội dung dòng đó (**bỏ** `\n` và `\r` cuối dòng) trong **một datagram** bằng `sendto()`.
   Dòng rỗng (sau khi bỏ `\n`) thì **bỏ qua**, không gửi gì và không in gì.
2. Đợi datagram phản hồi tối đa **1 giây** (dùng `select`/`poll`, hoặc `SO_RCVTIMEO`).
   - Nhận được: in nội dung datagram ra **stdout**, thêm một `\n`, rồi `fflush`.
   - Quá 1 giây: in `TIMEOUT` và `\n`, rồi **vẫn tiếp tục** với dòng sau.

Hết stdin (EOF): thoát với mã `0`. Địa chỉ IP không hợp lệ: in lỗi ra `stderr`, thoát mã **khác 0**.
Phản hồi dài tối đa 2048 byte.

## Ví dụ (server là bài *udp-calc*)

```
stdin          stdout
12 + 30        42
-7 / 2         -3
5 % 0          ERROR div0
```

## Ràng buộc
- Phản hồi có thể **rỗng** (in một dòng trống — đó không phải TIMEOUT), dài đúng 2048 byte, hoặc chứa `0x00`
  (in đúng từng byte bằng `fwrite`).
- Dòng nhập giữ nguyên dấu cách/tab ở đầu và cuối (chỉ bỏ `\n`, `\r`); dòng chỉ có `\r` là dòng rỗng; dòng
  cuối có thể không có `\n`. Có thể nhiều lần TIMEOUT liên tiếp.

## Bộ chấm kiểm tra
Bộ chấm dựng server UDP giả, chạy chương trình của bạn và kiểm tra: mỗi dòng đến server thành **đúng một**
datagram **không có `\n`**; phản hồi được in đúng; im lặng thì in `TIMEOUT` sau khoảng 1 giây (không sớm,
không treo mãi) mà vẫn phục vụ dòng sau.

## Bẫy hay gặp
- `fgets` giữ lại `\n`: nếu không bỏ, datagram gửi đi thừa một byte và server `udp-calc` sẽ trả `ERROR syntax`.
- `recvfrom()` không có thời gian chờ sẽ **treo vĩnh viễn** khi gói tin (hoặc phản hồi) bị mất. UDP không đảm bảo giao hàng.
- UDP bảo toàn ranh giới thông điệp: một `sendto` ↔ một `recvfrom`. Không cần (và không nên) ghép dòng như TCP.
- Phản hồi không có `\0` ở cuối: tự thêm hoặc in bằng `fwrite(buf, 1, n, stdout)`.
