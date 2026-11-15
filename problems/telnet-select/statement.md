# telnet_server đăng nhập và chạy lệnh (Bài tập 3.2)

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

## Gợi ý
- Như lecture notes: `system("<lệnh> > out.txt 2>&1")` rồi đọc tệp. Mỗi client nên dùng **tên tệp
  riêng** (ví dụ theo fd), nếu không kết quả của hai client sẽ lẫn nhau.
- Vì sao cần `OUTPUT <n>` mà không gửi thẳng kết quả? Vì kết quả có thể rỗng hoặc nhiều dòng, nên
  client cần biết **khi nào hết**.
- Hạn chế: trong lúc `system()` chạy, cả server bị chặn. Bài *telnet-fork* khắc phục điều này.
