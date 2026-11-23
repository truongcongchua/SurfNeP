---
title: "Quản lý nhiều client: giới hạn N & broadcast"
chapter: 3
ref: "Lecture notes §3.5–3.6; dạng đề giữa kỳ"
---

## Dạng đề giữa kỳ
> "Tạo ứng dụng server/client dùng TCP/UDP phục vụ một bài toán với số lượng tối đa N client."

Tách thành hai việc:
1. **Phục vụ nhiều client cùng lúc:** chọn một trong `select`, đa luồng (thread), hoặc `fork` (bảng chọn ở cuối thẻ).
2. **Không cho quá N client:** đếm số client đang kết nối.

## Lưu thông tin từng client
Mỗi client cần **hồ sơ riêng**: socket, bộ đệm đang ghép dở, tên, đã đăng nhập chưa...
```c
typedef struct {
    int    fd;             // -1 nghĩa là ô trống
    char   buf[4096];      // bộ đệm ghép dòng RIÊNG của client này
    size_t len;
    char   name[32];
    int    logged_in;
} Client;

Client clients[MAX_CLIENTS];
int nclients = 0;

// lúc khởi động: đánh dấu mọi ô là trống
for (int i = 0; i < MAX_CLIENTS; i++) clients[i].fd = -1;
```
Dùng chung một bộ đệm cho mọi client là lỗi kinh điển: dòng của client A bị trộn với client B.

## Giới hạn N client
```c
int c = accept(listen_fd, NULL, NULL);
if (nclients >= N) {
    send(c, "FULL\n", 5, 0);    // báo cho client biết (nếu đề yêu cầu)
    close(c);                   // đóng ngay, không lưu vào danh sách
} else {
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (clients[i].fd == -1) {               // tìm ô trống
            clients[i].fd = c; clients[i].len = 0; clients[i].logged_in = 0;
            break;
        }
    nclients++;
    send(c, "WELCOME\n", 8, 0);
}
```
- Khi đã đủ N **vẫn phải `accept`** rồi từ chối. Nếu không `accept`, client mới bị treo trong hàng chờ mà không biết gì.
- **Giảm `nclients` ở mọi đường client rời đi:** gõ `QUIT`, `recv` trả `0`, `recv` lỗi. Sót một đường → bộ đếm không bao giờ giảm, server tưởng đầy mãi.

```c
void drop(int i) {                 // gọi hàm này ở MỌI chỗ client rời đi
    close(clients[i].fd);
    clients[i].fd = -1;
    nclients--;
}
```

## Broadcast: gửi cho mọi người (phòng chat)
```c
for (int i = 0; i < MAX_CLIENTS; i++)
    if (clients[i].fd != -1 && clients[i].fd != sender_fd)   // bỏ qua ô trống và người gửi
        send(clients[i].fd, msg, msglen, 0);
```
- Nếu dùng **đa luồng**: mảng `clients` là dữ liệu chung của nhiều luồng → phải **khoá mutex** khi đọc/sửa (xem thẻ *pthread & mutex*).
- Client rời đi trong lúc đang duyệt: chỉ đánh dấu `fd = -1`, đừng dịch mảng khi đang lặp.

## Chọn kỹ thuật nào?
| Bài toán | Nên chọn | Vì sao |
|---|---|---|
| Các client dùng **chung dữ liệu** (chat, bảng key-value) | `select` | một luồng, không cần khoá |
| | hoặc thread + mutex | code từng client viết tuần tự, dễ đọc |
| Mỗi client **độc lập**, không chia sẻ gì | `fork` | đơn giản, client này lỗi không ảnh hưởng client khác |

Đừng dùng `fork` cho bài cần dữ liệu chung: mỗi tiến trình con có **bản sao riêng**, sửa ở con này con kia không thấy.

## Lỗi hay gặp
- **Server báo đầy dù không ai kết nối.** Quên giảm bộ đếm ở một đường thoát (hay gặp nhất là khi client tắt đột ngột, `recv` trả 0).
- **Người gửi nhận lại chính tin của mình.** Đề yêu cầu "tất cả trừ người gửi" nhưng quên điều kiện `!= sender_fd`.
- **Crash khi nhiều client.** `N` lớn hơn kích thước mảng `MAX_CLIENTS`.
