# Server Telnet đăng nhập và xử lý lệnh

Viết `./telnet_server <cổng>` dùng **`select()`** phục vụ nhiều client.
**Không được dùng:** `fork` (trực tiếp), `pthread`, `poll`, `epoll`. Gọi `system()` thì được.

## Giao thức (mỗi thông điệp từ client là một dòng, bỏ `\r` cuối dòng)

**1. Đăng nhập.** Dòng đầu có dạng `<user> <pass>` (đúng một dấu cách). Nếu cặp này có trong tệp
`accounts.txt` ở thư mục hiện hành (mỗi dòng một cặp `user pass`) thì server trả `LOGIN OK`.
Ngược lại trả `LOGIN FAIL` và client được thử lại. Mọi dòng gửi trước khi đăng nhập thành công
đều được coi là một lần đăng nhập.

**2. Chạy lệnh.** Sau khi đăng nhập, mỗi dòng là một lệnh shell. Server chạy lệnh, gom **cả stdout
lẫn stderr**, rồi gửi:

```
OUTPUT <n>\n
<đúng n byte kết quả>
```

**3. Thoát.** Dòng `exit` thì server trả `BYE` và đóng kết nối.

## Ví dụ

```
→ admin admin          ← LOGIN OK
→ echo hello           ← OUTPUT 6\nhello\n
→ true                 ← OUTPUT 0\n
→ exit                 ← BYE
```

## Ràng buộc và bộ chấm kiểm tra
- Đăng nhập phải **khớp nguyên dòng** với một dòng của `accounts.txt` (phân biệt hoa thường; thừa/thiếu dấu cách,
  tab, tiền tố như `admin adm` đều là `LOGIN FAIL`). Bỏ `\r` cuối dòng. Mọi dòng trước khi đăng nhập thành công,
  kể cả `exit`, đều là một lần đăng nhập.
- Một dòng lệnh dài tới 1000 byte và có thể gồm **nhiều lệnh** (`echo a; echo b`, `a | b`): gom kết quả của cả
  dòng (gợi ý: `system("{ <lệnh>\n} > tệp 2>&1")`). Dòng lệnh rỗng → `OUTPUT 0`. Chỉ đúng dòng `exit` mới thoát
  (`exit 3`, `exitnow` là lệnh shell bình thường). Đã đăng nhập rồi thì dòng giống tài khoản (`admin admin`) cũng chỉ
  là một lệnh shell. Nếu `exit` nằm giữa nhiều dòng gửi dính nhau: chạy các lệnh trước nó, trả `BYE`, đóng, bỏ các dòng sau.
- `n` là **số byte thật** của kết quả: kết quả có thể chứa byte `0x00` (không dùng `strlen`), có thể rỗng, hoặc
  lớn tới vài MB.
- Lệnh có thể đến từng byte một, hoặc dòng đăng nhập + hàng chục lệnh dính nhau trong một lần gửi.
- Chương trình chạy với giới hạn 256 file descriptor: bộ chấm thử 300 lần đăng nhập sai và 300 phiên liên tiếp (nhớ `fclose`/`close`).

## Gợi ý
- Như lecture notes: `system("{ <lệnh>\n} > out.txt 2>&1")` rồi đọc tệp. Mỗi client nên dùng **tên tệp
  riêng** (ví dụ theo fd), nếu không kết quả của hai client sẽ lẫn nhau.
- Vì sao cần `OUTPUT <n>` mà không gửi thẳng kết quả? Vì kết quả có thể rỗng hoặc nhiều dòng, nên
  client cần biết **khi nào hết**.
- Hạn chế: trong lúc `system()` chạy, cả server bị chặn. Bài *telnet-fork* khắc phục điều này.
