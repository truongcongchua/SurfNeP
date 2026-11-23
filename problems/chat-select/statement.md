# Phòng chat đa client với select

Viết **chat_server** chạy bằng `./chat_server <cổng>`, dùng **`select()`** để phục vụ nhiều
client trong **một tiến trình, một luồng** (không dùng `fork`, `pthread`, `poll`).
Hỗ trợ tối thiểu 30 client cùng lúc.

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

## Ràng buộc
- `client_id`, `client_name` dài 1–32 byte, không chứa dấu cách; dòng đăng ký phải **khớp chính xác** dạng
  `id: name` (dấu cách thừa ở đầu/cuối/giữa → `ERROR`). Mỗi dòng tối đa 1000 byte, không chứa `0x00`.
- Nội dung tin được chuyển **nguyên vẹn** (kể cả dòng rỗng, dấu cách, dấu `:`), chỉ bỏ `\r` cuối dòng.
- Kết nối mới luôn ở trạng thái **chưa đăng ký**, kể cả khi dùng lại chỗ của client cũ.
- Chương trình chạy với giới hạn 256 file descriptor (bộ chấm cho 300 lượt vào-ra phòng).
- Tới 30 client cùng lúc; tới 1000 tin dồn trong một lần gửi; tin của cùng một người phải đến **đúng thứ tự**.

## Những điều bộ chấm sẽ kiểm tra
- Dòng bị cắt thành nhiều lần `send`, hoặc nhiều dòng dính trong một lần `send`.
- Một client gửi dở nửa dòng rồi im lặng không được làm server "đứng" với client khác.
- Client rời phòng giữa chừng.
- Mã nguồn có thực sự dùng `select()`.

## Kiến thức nền
- Lecture notes §3.1: chế độ blocking/non-blocking.
- Lecture notes §3.5: `select()`, `fd_set`, `FD_SET/FD_ISSET`, vì sao phải dựng lại tập fd mỗi vòng lặp.
- Bài nền: *select-echo*, *tcp-recv-line* (mỗi client cần **bộ đệm riêng** để ghép dòng).
