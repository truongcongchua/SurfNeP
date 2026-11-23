---
title: "Đọc/ghi tệp trong server"
chapter: 2
ref: "Lecture notes: lab07 (fopen), lab08 (open/read/write)"
---

## Hiểu nhanh
Làm việc với tệp có 3 bước giống mở một cuốn sổ: **mở** → **đọc/ghi** → **đóng**. Trong C có hai bộ hàm làm việc này:

| | Bộ `stdio` (dễ dùng, khuyên dùng) | Bộ POSIX (cấp thấp) |
|---|---|---|
| Mở | `FILE *f = fopen(path, "rb")` | `int fd = open(path, O_RDONLY)` |
| Đọc / ghi | `fread` / `fwrite` | `read` / `write` |
| Đóng | `fclose(f)` | `close(fd)` |
| Có bộ đệm? | có (ghi vào RAM trước, lát sau mới xuống tệp) | không |

## Chế độ mở tệp với `fopen`
| Chế độ | Nghĩa | Tệp chưa có | Tệp đã có |
|---|---|---|---|
| `"rb"` | đọc | trả `NULL` | đọc từ đầu |
| `"wb"` | ghi mới | tạo mới | **xoá sạch** rồi ghi |
| `"ab"` | ghi nối đuôi | tạo mới | ghi tiếp vào **cuối** |

Chữ `b` (binary) nghĩa là đọc/ghi đúng từng byte, không biến đổi gì. Với dữ liệu nhận từ mạng nên luôn dùng `b`.

## Đọc cả tệp rồi gửi qua socket
```c
FILE *f = fopen(path, "rb");
if (f == NULL) {                       // tệp không tồn tại / không có quyền
    send_str(fd, "ERROR not found\n");
    return;
}
char buf[4096];
size_t n;
while ((n = fread(buf, 1, sizeof buf, f)) > 0)   // đọc từng khúc tối đa 4096 byte
    send(fd, buf, n, 0);                         // gửi đúng n byte vừa đọc (như html.c)
fclose(f);
```
Socket blocking: `send` tự chờ tới khi gửi hết `n` byte.

## Ghi thêm vào cuối tệp (ghi log)
```c
FILE *f = fopen("log.txt", "ab");      // "ab": giữ nguyên nội dung cũ, ghi tiếp vào cuối
if (f) {
    fwrite(data, 1, n, f);             // ghi n byte (dữ liệu nhận từ client)
    fclose(f);                         // đóng = đẩy hết xuống đĩa
}
```
Nếu muốn giữ tệp mở lâu (ghi nhiều lần) thì gọi `fflush(f)` sau mỗi lần ghi để dữ liệu xuống đĩa ngay.

## Ghi một dòng có định dạng
```c
fprintf(f, "%s %s\n", ip, message);    // giống printf nhưng ghi vào tệp
```

## Lỗi hay gặp
- **Log chỉ còn dòng cuối cùng.** Mở bằng `"w"`/`"wb"` nên mỗi lần mở là xoá sạch. Sửa: dùng `"a"`/`"ab"`.
- **Mở tệp ra thấy rỗng dù đã ghi.** Dữ liệu còn nằm trong bộ đệm. Sửa: `fflush` hoặc `fclose`.
- **Dữ liệu bị cụt.** Dùng `fgets`/`strlen` cho dữ liệu có thể chứa byte `0`. Sửa: dùng `fread`/`fwrite` với số byte cụ thể.
- **Chương trình crash khi tệp không có.** Không kiểm tra `fopen` trả `NULL`.
- **Client mới không thấy nội dung tệp mới.** Đọc tệp một lần lúc khởi động, trong khi đề yêu cầu đọc lại mỗi khi có client.
- **Hết descriptor sau một thời gian.** Quên `fclose` ở nhánh lỗi (`return` sớm).
