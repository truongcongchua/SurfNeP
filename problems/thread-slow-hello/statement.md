# Server chào chậm, mỗi client một luồng

Viết server `./server <cổng>` làm đúng một việc với mỗi client: **đợi 1 giây** (`sleep(1)`, giả làm việc xử lý chậm),
gửi `Hello!\n` (7 byte), rồi đóng kết nối. Server **không đọc** gì từ client.

Mỗi client phải được phục vụ trong **một luồng riêng** tạo bằng `pthread_create`, nên 50 client đến cùng lúc đều nhận
lời chào sau khoảng 1 giây, chứ không phải 50 giây. **Không được dùng:** `fork`, `select`, `poll`, `epoll`.

## Bài này để làm gì
Bước khởi động cho `thread-echo`. Nó giữ nguyên khung "accept → tạo luồng → luồng tự đóng socket" nhưng bỏ vòng
`recv`/`send` (đã luyện ở `tcp-echo`), và dùng `sleep(1)` để **ép** lỗi đa luồng lộ ra mỗi lần chạy:

| Kỹ thuật dùng ở `thread-echo` | Làm ở bài này |
|---|---|
| Mỗi client một luồng: `pthread_create` trong vòng `accept` | Thiếu thì client thứ hai phải chờ client thứ nhất |
| `malloc` một ô `int` chứa `fd` cho từng luồng, luồng `free` sau khi đọc (luyện ở `thread-args`) | Có `sleep(1)` nên truyền `&client` là sai **chắc chắn**: mọi luồng thức dậy cùng gửi cho client cuối |
| `pthread_detach`: luồng tự dọn, luồng chính không chờ | Gọi `pthread_join` sẽ làm luồng chính chờ 1 giây mỗi client |
| Luồng tự `close(fd)` khi xong | Quên thì hết 256 file descriptor ở test 300 client |

## Ràng buộc và bộ chấm kiểm tra
- Lời chào là đúng 7 byte `Hello!\n`, gửi **sau** khoảng 1 giây kể từ lúc client kết nối (không sớm hơn 0,85 giây, không quá
  2 giây), sau đó server đóng kết nối. Không gửi thêm byte nào.
- Tới 50 client cùng lúc. Dùng `listen(server_socket, 64)`.
- Client có thể đóng kết nối ngay (không chờ lời chào), hoặc `shutdown` chiều gửi, hoặc kết nối rồi không đọc gì cả: các
  client khác vẫn phải được chào đúng hạn và server không được thoát.
- Chương trình chạy với giới hạn **256 file descriptor**; bộ chấm cho 300 client (mỗi đợt 50 client cùng lúc).
- Không in gì ra stdout.

## Ví dụ

```
t = 0,0s   client A kết nối
t = 0,5s   client B kết nối
t = 1,0s   A nhận "Hello!\n", rồi bị đóng kết nối
t = 1,5s   B nhận "Hello!\n", rồi bị đóng kết nối
```

## Gợi ý
- Khung giống `pthread_server.c`, dòng `sleep(1);` nằm trong hàm luồng ngay sau khi lấy `fd` ra:
  ```c
  void *greet(void *arg) {
      int client = *(int *)arg;
      free(arg);
      sleep(1);
      send(client, "Hello!\n", 7, 0);
      close(client);
      return NULL;
  }
  ```
- Trong vòng `accept`: `int *p = malloc(sizeof *p); *p = client; pthread_create(&t, NULL, greet, p); pthread_detach(t);`.
  Đặt `sleep(1)` ở luồng chính (thay vì trong hàm luồng) hoặc gọi `pthread_join` đều biên dịch được nhưng trượt test đồng thời, vì luồng chính bị giữ lại 1 giây cho mỗi client.
- Nếu `pthread_create` trả về khác `0`, hãy `close(client)` và `free(p)` tại chỗ.
