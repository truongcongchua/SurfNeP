# Gửi hồ sơ sinh viên dạng nhị phân

Bài tập 2.4: viết **sv_client** nhập thông tin sinh viên, **đóng gói** thành bản ghi nhị phân rồi gửi cho server.
Đây là phía client của bài *sv-struct*, nên bạn có thể kiểm tra chéo bằng server do chính bạn viết ở đó.

```
./sv_client <địa chỉ IP> <cổng>
```

## Dữ liệu nhập (stdin)
Mỗi sinh viên là **4 dòng** liên tiếp. Không in lời nhắc nào ra stdout.

```
20201234              ← MSSV (số nguyên không dấu 32 bit)
Nguyễn Văn A          ← họ tên (UTF-8, có thể có dấu cách, 1 … 100 byte)
2002-04-10            ← ngày sinh YYYY-MM-DD
3.99                  ← điểm trung bình, tối đa 2 chữ số thập phân
```

Có thể nhập **nhiều sinh viên** liên tiếp; stdin kết thúc (EOF) thì đóng kết nối và thoát mã `0`.
Dữ liệu nhập luôn hợp lệ.

## Bản ghi gửi đi (số nguyên theo thứ tự mạng, big-endian, không padding)

| Trường | Kích thước | Ghi chú |
|---|---|---|
| `mssv` | 4 byte, `uint32` | |
| `name_len` | 1 byte | số **byte** của tên (không phải số ký tự) |
| `name` | `name_len` byte | không có ký tự kết thúc `\0` |
| `year` | 2 byte, `uint16` | |
| `month` | 1 byte | |
| `day` | 1 byte | |
| `gpa100` | 2 byte, `uint16` | điểm × 100, làm tròn (`3.99` → `399`) |

## Phản hồi của server
Với mỗi bản ghi, server trả một dòng (`OK` hoặc `ERROR`). Client đọc dòng đó và in ra **stdout** đúng như nhận được,
kèm `\n` (một dòng cho mỗi bản ghi). Nếu là `ERROR` thì server sẽ đóng kết nối: client dừng gửi và thoát mã `0`.

Không kết nối được: in lỗi ra `stderr`, thoát mã **khác 0**.

## Ràng buộc
- Dòng nhập có thể kết thúc bằng `\r\n`; dòng cuối có thể không có `\n`; stdin có thể đến từng mảnh nhỏ.
- Điểm như `0.29`, `0.57`, `1.13`, `2.01` phải ra đúng `29`, `57`, `113`, `201` (đừng ép kiểu thẳng `double`).
- MSSV tới `4294967295`; tên tới 100 byte UTF-8. Phản hồi `OK\n` có thể đến từng byte: đọc đủ một dòng.
- Gửi bản ghi sau **chỉ khi** đã nhận phản hồi của bản ghi trước. Server có thể đóng kết nối mà không trả lời:
  client không được treo hay chết vì `SIGPIPE`.

## Bẫy hay gặp
- Gửi thẳng một `struct`: bị **padding** và sai thứ tự byte. Hãy tự ghép từng trường vào một mảng byte
  (`htonl`, `htons`) rồi `send` một lần.
- `3.99 * 100` trong `double` có thể ra `398.99999…`; ép kiểu thẳng sang số nguyên sẽ cắt thành `398`.
  Dùng `lround()` hoặc đọc phần nguyên và phần thập phân riêng.
- `fgets` giữ lại `\n` ở cuối: bỏ nó trước khi tính `name_len`.
- `stdout` là tệp/pipe thì được đệm đầy: `fflush(stdout)` sau mỗi dòng phản hồi.
