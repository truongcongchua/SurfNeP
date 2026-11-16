---
title: "Quản lý nhiều client: giới hạn N & broadcast"
chapter: 3
ref: "Lecture notes §3.5–3.6; dạng đề giữa kỳ"
---

## Dạng đề giữa kỳ
> "Tạo ứng dụng server/client dùng TCP/UDP phục vụ một bài toán với số lượng tối đa N client."

Gồm hai việc: **(1)** phục vụ đồng thời nhiều client (chọn select/poll hoặc thread), **(2)** áp đặt giới hạn N.

## Giới hạn N client
```c
if (nclients >= N) {
    send(c, "FULL\n", 5, 0);     // thông báo trước, nếu đề yêu cầu
    close(c);                    // rồi đóng ngay, không đưa vào danh sách
} else {
    add_client(c); nclients++;
    send(c, "WELCOME\n", 8, 0);
}
```
Giảm `nclients` ở **mọi** đường client rời đi (`QUIT`, `recv` trả `0`, lỗi). Quên một nhánh → "rò rỉ chỗ", server tưởng đầy mãi.

Vẫn phải `accept` khi đầy (rồi từ chối), nếu không client xếp hàng trong hàng đợi `listen` và treo.

## Cấu trúc dữ liệu client
```c
typedef struct { int fd; char buf[4096]; size_t len; char name[32]; int logged_in; } Client;
Client clients[MAX_CLIENTS];     // fd = -1 là ô trống
```
Mỗi client có **bộ đệm và trạng thái riêng** (đã đăng nhập chưa, đã gửi nửa dòng chưa...). Dùng chung một bộ đệm là lỗi kinh điển.

## Broadcast (chat room)
```c
for (int i = 0; i < MAX_CLIENTS; i++)
    if (clients[i].fd >= 0 && clients[i].fd != sender_fd)
        send(clients[i].fd, msg, msglen, 0);
```
- Đa luồng: bảng `clients` là dữ liệu chung → **khoá mutex** khi duyệt/sửa.
- Một `send` tới client chậm có thể chặn; với bài thi thường chấp nhận được, nhưng tránh giữ khoá lâu.
- Client rời đi trong lúc duyệt → đánh dấu `fd = -1` rồi dọn sau, đừng xoá khi đang lặp.

## Chọn kỹ thuật
| Yêu cầu | Chọn |
|---|---|
| Dữ liệu chung (bảng key-value, chat room) | **select/poll** (không cần khoá) hoặc **thread + mutex** |
| Mỗi client độc lập, dễ cài | fork |
| Hàng nghìn client | epoll (ngoài phạm vi môn) |

## Bẫy thường gặp
- Đếm client sai khi client rời đột ngột.
- Gửi tin cho cả người gửi khi đề yêu cầu "tất cả trừ người gửi".
- Dùng `fork` cho bài cần dữ liệu chung (mỗi tiến trình con thấy bản sao riêng).
- Tràn mảng khi `N` lớn hơn kích thước mảng khai báo.
