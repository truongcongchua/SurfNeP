# Client in vé ra tệp

Chức năng **in vé** của bài tập lớn đặt vé máy bay, nhìn từ phía **client**: đăng nhập, xin nội dung vé, nhận về
đúng từng byte rồi ghi ra tệp (để mở hoặc in). Cùng ý với "tải tệp xuống" của FTP (§4.2.2), nhưng đơn giản hơn: chỉ một
kết nối, nội dung đi ngay sau dòng báo độ dài.

Viết `./client <ip> <cổng> <user> <pass> <mã vé> <tệp ra>`.

## Hội thoại

Bộ chấm đóng vai server. Mọi dòng kết thúc bằng `\n`.

```
(client kết nối)
server → client : 100 OK WELCOME
client → server : LOGIN <user> <pass>
server → client : 100 OK <user>
client → server : PRINT <mã vé>
server → client : 120 FILE <n>
server → client : <đúng n byte nội dung vé, không có ký tự thừa phía sau>
client → server : QUIT
server → client : 100 OK
(client đóng kết nối, ghi tệp, thoát mã 0)
```

- Client phải **chờ** dòng `100 OK WELCOME` (và từng phản hồi) trước khi gửi lệnh tiếp theo.
- `<n>` là số thập phân (0 ≤ n ≤ 5 000 000). Nội dung là **nhị phân bất kỳ**: có thể chứa byte `0x00`, ký tự xuống dòng,
  chuỗi giống một dòng phản hồi (`100 OK`...). Ghi vào `<tệp ra>` (tạo mới hoặc ghi đè) **đúng `n` byte**.
- Nội dung có thể đến **nhiều mảnh nhỏ**, hoặc dính ngay phía sau dòng `120 FILE n` trong cùng một lần gửi.
  Dòng `120 FILE n` cũng có thể đến từng phần.

## Khi có lỗi

Mọi phản hồi **không** đúng kỳ vọng (dòng đầu không phải `100 ...`; trả lời `LOGIN` khác `100 ...`; trả lời `PRINT` khác
`120 FILE <n>` hợp lệ), ví dụ `500 FULL`, `203 DENIED`, `202 NOT FOUND`, `204 LOGIN FIRST`:
1. in ra `stdout` một dòng `ERROR <nguyên dòng server gửi>`;
2. gửi `QUIT\n` (cố gắng, không bắt buộc nhận phản hồi) và đóng kết nối;
3. thoát mã **1**, và **không để lại tệp ra** (nếu đã có sẵn tệp cũ cùng tên thì để nguyên, không xóa, không ghi đè).

Các lỗi khác cũng thoát mã 1 và không tạo tệp: sai số tham số (in cách dùng), không kết nối được, server đóng kết nối
trước khi gửi đủ `n` byte (không để lại tệp dở), `n` không phải số thập phân hợp lệ.
Dù server khai báo `n` rất lớn, client **không** được cấp phát bộ nhớ theo `n`: hãy đọc từng mảnh và ghi thẳng ra tệp.

## Ví dụ

```
$ ./client 127.0.0.1 9000 an 1234 VN000001 ve.txt
$ echo $?
0
$ cat ve.txt
VE DIEN TU VN000001
HAN -> SGN
```

## Ràng buộc và bộ chấm kiểm tra
- Tệp ra phải giống **từng byte** với dữ liệu server gửi (kể cả `0x00`, `\r\n`, nội dung giống dòng phản hồi, 5 MB).
- Bộ chấm làm chậm server: gửi từng byte, chờ 0.3 giây trước `100 OK WELCOME`, tách dòng `120 FILE n` ra nhiều mảnh, nên client
  gửi sớm hơn quy định hoặc coi một lần `recv` là một thông điệp sẽ sai.
- `<user>`, `<pass>`, `<mã vé>` được ghép **nguyên văn** vào lệnh (không chứa dấu cách).

## Kiến thức nền
Giống phía nhận của bài *length-prefix*: đọc dòng tiêu đề từ bộ đệm, phần dữ liệu đã nhận thừa sau dòng đó thuộc về nội dung và
phải được ghi, rồi mới `recv` tiếp cho đủ `n` byte. Ghi tệp nhị phân bằng `fopen(..., "wb")` và `fwrite` (không dùng `fputs`/`%s`).
