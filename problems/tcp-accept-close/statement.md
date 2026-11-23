# Mở cổng và đón một client

Đây là bài khởi động cho server TCP: chỉ luyện **bốn hàm đầu tiên** và đúng thứ tự gọi chúng, chưa gửi hay nhận gì.

Viết server chạy bằng `./server <cổng>` làm đúng các việc sau rồi kết thúc:

1. `socket` tạo socket TCP.
2. `bind` gán địa chỉ (mọi IP của máy, cổng `<cổng>`).
3. `listen` chuyển sang chế độ nghe.
4. `accept` chờ **một** client kết nối tới.
5. Đóng socket của client và socket nghe, rồi thoát với mã `0`.

## Bốn hàm cần dùng (như `tcp_server.c`)

| Hàm | Làm gì | Trả về |
|---|---|---|
| `socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)` | tạo socket TCP | số fd, hoặc `-1` nếu lỗi |
| `bind(listener, (struct sockaddr*)&addr, sizeof(addr))` | gán IP + cổng cho socket | `0`, hoặc `-1` nếu lỗi (vd. cổng đang bị chiếm) |
| `listen(listener, 5)` | bắt đầu nghe; `5` là số client được xếp hàng chờ | `0`, hoặc `-1` nếu lỗi |
| `accept(listener, NULL, NULL)` | **chờ** tới khi có client, trả về socket **mới** dành riêng cho client đó | số fd mới, hoặc `-1` nếu lỗi |

Điền địa chỉ như trong `tcp_server.c`:

```c
struct sockaddr_in addr;
addr.sin_family = AF_INET;
addr.sin_port = htons(atoi(argv[1]));   // cổng lấy từ dòng lệnh, nhớ htons
addr.sin_addr.s_addr = INADDR_ANY;      // nhận kết nối trên mọi địa chỉ IP của máy
```

Sau mỗi hàm có thể lỗi, kiểm tra kết quả: lỗi thì `perror("tên hàm")`, đóng những gì đã mở rồi `exit(EXIT_FAILURE)`.

## Hai socket khác nhau
`socket` trả về socket **nghe** (`listener`): nó chỉ để đón client mới. `accept` trả về socket **của client** (`client`): sau này dùng nó để `recv`/`send`. Bài này chưa dùng `client` để làm gì, chỉ `close` nó.

## Ràng buộc và bộ chấm kiểm tra
- Server **chờ ở `accept`** cho tới khi có client; không được thoát trước khi có client.
- Chỉ đón **một** client. Không gửi gì cho client, không đọc gì từ client.
- Sau khi đón client: đóng kết nối (client sẽ thấy kết nối bị đóng) và kết thúc với mã `0`.
- Bộ chấm thử cổng bằng cách thật sự kết nối tới, nên thiếu `listen` hoặc sai cổng (quên `htons`) sẽ báo `NL`.

## Ví dụ

```
$ ./server 9000          ← đứng chờ
(client kết nối tới cổng 9000)
$                        ← server đóng kết nối và thoát
```

## Kiến thức nền
`2-Chap2/tcp_server.c`: bài này là phần đầu của file đó (từ `socket` tới `accept`).
