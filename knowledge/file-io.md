---
title: "Đọc/ghi tệp trong server"
chapter: 2
ref: "Lecture notes: lab07 (fopen), lab08 (open/read/write)"
---

## Hai họ hàm
| | stdio (`FILE *`) | POSIX (`int fd`) |
|---|---|---|
| Mở | `fopen(path, "rb"/"ab"/"wb")` | `open(path, O_WRONLY\|O_CREAT\|O_APPEND, 0644)` |
| Đọc/ghi | `fread`/`fwrite` | `read`/`write` |
| Đóng | `fclose` | `close` |
| Đệm | có (đệm ở user space) | không |

## Đọc nguyên tệp (để gửi qua socket)
```c
FILE *f = fopen(path, "rb");          // "rb": nhị phân, không biến đổi \n
if (!f) { /* báo lỗi */ }
char buf[4096]; size_t n;
while ((n = fread(buf, 1, sizeof buf, f)) > 0) send_all(fd, buf, n);
fclose(f);
```

## Ghi nối tiếp (log)
```c
FILE *f = fopen(logpath, "ab");       // "ab": append, tạo nếu chưa có, KHÔNG ghi đè
fwrite(data, 1, n, f);
fflush(f);                            // đẩy xuống tệp ngay, không chờ đủ bộ đệm
fclose(f);
```

## Bẫy thường gặp
- Dùng `"w"`/`"wb"` thay vì `"a"`/`"ab"` → ghi đè dữ liệu của client trước.
- Quên `fflush`/`fclose` → dữ liệu còn nằm trong bộ đệm, kiểm tra tệp thấy rỗng.
- Dùng `fgets`/`strlen` với dữ liệu nhị phân (chứa `'\0'`): dùng `fread`/`fwrite` với số byte cụ thể.
- Đọc tệp **một lần** lúc khởi động khi đề yêu cầu đọc lại mỗi khi có client mới.
- Không kiểm tra `fopen` trả `NULL` → crash khi tệp không tồn tại.
- Đường dẫn do client gửi chứa `..` → lọt ra ngoài thư mục gốc (cần chặn, xem bài HTTP).
- Quên `fclose` trong nhánh lỗi → rò rỉ descriptor.
