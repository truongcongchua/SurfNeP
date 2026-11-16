# Server chat đa luồng

Viết **chat_server** `./chat_server <cổng>` với **cùng giao thức** như bài *chat-select*, nhưng mỗi client
được phục vụ bởi **một luồng** (`pthread_create`). **Không được dùng:** `select`, `poll`, `epoll`, `fork`.

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

## Điểm khó: dữ liệu dùng chung
Danh sách client (fd, id) được **mọi luồng** đọc khi broadcast và được sửa khi client vào hoặc rời.
Bảo vệ nó bằng `pthread_mutex_t`. Câu hỏi đáng nghĩ: có nên giữ mutex trong lúc `send`? Nếu một
client nhận chậm thì sao?

## Kiến thức nền
Lecture notes §3.4; code mẫu `pthread_chatroom.c`. Bài nền: *thread-echo*, *chat-select*.
