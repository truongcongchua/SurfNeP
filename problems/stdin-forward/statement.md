# Chuyển tiếp stdin ra stdout bằng read/write

Viết chương trình **không có tham số**: chép mọi byte từ **stdin** ra **stdout**, đúng như `cat`, nhưng phải dùng
`read(STDIN_FILENO, ...)` và `write(STDOUT_FILENO, ...)` (như lab08), **không** dùng `fgets`/`scanf`/`printf`.

- Đọc được bao nhiêu thì ghi ra ngay bấy nhiêu, **không đợi** hết stdin rồi mới ghi.
- Khi stdin kết thúc (EOF, tức `Ctrl+D`): thoát với mã `0`.
- stdout chỉ chứa dữ liệu chép từ stdin, không in thêm gì (thông báo nếu có thì ra `stderr`).

Bài này là bước khởi động cho `tcp-client-stdin`: ở đó bạn sẽ thay `write(STDOUT_FILENO, ...)` bằng `send(socket, ...)`.

## Ràng buộc
- Dữ liệu là byte bất kỳ: có thể chứa `0x00`, `\r`, không có `\n` ở cuối, hoặc rỗng hoàn toàn.
- Một dòng có thể dài tới 200 KB, tổng dữ liệu tới vài MB.
- Dữ liệu có thể đến từng mảnh nhỏ, cách nhau một khoảng thời gian: mỗi mảnh phải xuất hiện ở stdout trong
  chưa đầy một giây sau khi được đưa vào, kể cả khi mảnh đó **chưa** kết thúc bằng `\n`.

## Ví dụ

```
stdin : "xin chao\nthe gioi\n"   →   stdout: "xin chao\nthe gioi\n"
stdin : (rỗng)                   →   stdout: (rỗng)
```

## Gợi ý
- `ssize_t n = read(STDIN_FILENO, buf, sizeof buf);` trả về số byte **thực sự đọc được** (có thể ít hơn `sizeof buf`),
  `0` khi hết stdin, `-1` khi lỗi. Ghi lại **đúng `n` byte**: `write(STDOUT_FILENO, buf, n)`.
- Dữ liệu không phải xâu C: không dùng `strlen`, không cần `'\0'` ở cuối.
- Khi stdin là bàn phím (hoặc ống dẫn), `read` trả về ngay khi có dữ liệu thay vì chờ đầy bộ đệm; đó chính là lý do
  `read` hợp với bài tcp-client-stdin hơn `fread`.
