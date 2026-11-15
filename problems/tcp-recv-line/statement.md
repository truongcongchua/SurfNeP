# Hàm recv_line

Hầu hết giao thức trong môn học trao đổi theo **dòng**. Viết hàm (không viết `main`):

```c
#include <sys/types.h>
ssize_t recv_line(int fd, char *buf, size_t cap);
```

Hàm hoạt động như `fgets` nhưng đọc từ socket `fd`:

- Đọc byte cho đến khi gặp `'\n'` (**có** lưu `'\n'` vào `buf`), hoặc khi đã lưu `cap - 1` byte,
  hoặc khi đối phương đóng kết nối.
- Luôn kết thúc `buf` bằng `'\0'`. Trả về **số byte đã lưu** (không tính `'\0'`).
- Đối phương đóng kết nối mà chưa đọc được byte nào thì trả về `0`. Lỗi thì trả về `-1`.
- **Không được làm mất dữ liệu:** byte nào chưa trả về trong lần gọi này phải được trả về ở lần
  gọi sau. Dữ liệu có thể chứa byte `0x00`.

Bộ chấm gọi `recv_line` liên tục trên một socket, phía bên kia gửi dữ liệu thành các mảnh có kích
thước và độ trễ khác nhau. Mỗi lần gọi in ra `<giá trị trả về> [<nội dung>]`, trong đó `\n` hiện
thành `\n`, `\r` thành `\r` và byte 0 thành `\0`.

## Ví dụ (cap = 5)

Phía kia gửi `abcdefghij\n` rồi đóng:

```
4 [abcd]
4 [efgh]
3 [ij\n]
0 []
```

## Gợi ý
Cách đơn giản nhất là `recv` **từng byte**. Cách nhanh hơn: một bộ đệm `static` giữ phần thừa
(cách này chỉ đúng khi dùng với một socket; hãy nghĩ cách làm cho nhiều socket ở bài *chat-select*).
