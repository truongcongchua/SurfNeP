# Phòng chat đa client với poll

Viết lại **chat_server** của bài *chat-select* bằng **`poll()`** thay cho `select()`, cùng giao thức.
**Không được dùng:** `select`, `epoll`, `fork`, `pthread`.

## Giao thức

Mọi thông điệp là một **dòng** kết thúc bằng `\n` (bỏ qua `\r` nếu có ở cuối dòng).

**1. Đăng ký tên.** Dòng đầu tiên client gửi phải có dạng:

```
client_id: client_name
```

`client_id` và `client_name` là các xâu **khác rỗng, không chứa dấu cách**, ngăn cách nhau bởi
đúng chuỗi `": "` (dấu hai chấm và một dấu cách).
- Hợp lệ: server trả `OK <client_id>`.
- Không hợp lệ: server trả `ERROR` và tiếp tục chờ client gửi lại.

**2. Chat.** Sau khi đăng ký, mỗi dòng `L` mà client `id` gửi được chuyển tới **mọi client
khác đã đăng ký** dưới dạng `id: L`. Không gửi lại cho chính người gửi và không gửi cho client
chưa đăng ký.

**3. Ngắt kết nối.** Khi một client đóng kết nối, server dọn dẹp và tiếp tục phục vụ những
client còn lại.

## Ví dụ

```
A → server : abc: An
server → A : OK abc
B → server : xyz Binh          (sai cú pháp)
server → B : ERROR
B → server : xyz: Binh
server → B : OK xyz
A → server : xin chao
server → B : abc: xin chao
```

## So sánh với select()
- `poll` nhận **mảng `struct pollfd`**, không bị giới hạn `FD_SETSIZE` (1024).
- Không cần dựng lại tập fd mỗi vòng: kernel ghi kết quả vào trường `revents`, `events` giữ nguyên.
- Xoá client khỏi mảng: chép phần tử cuối vào chỗ trống, nhưng cẩn thận đừng bỏ qua phần tử vừa chép.
- `POLLHUP`/`POLLERR` cũng báo client đã rời đi.
