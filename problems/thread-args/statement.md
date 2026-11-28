# Mỗi số một luồng

Đọc từ **stdin**: dòng đầu là số nguyên `n`, tiếp theo là `n` số nguyên `a[0] … a[n-1]` (cách nhau bởi dấu cách hoặc
xuống dòng). Với **mỗi số**, tạo **một luồng** bằng `pthread_create`; luồng đó tính `a[i] * a[i]` và cất vào ô `sq[i]`.
Chờ mọi luồng xong rồi in ra stdout `n` dòng: dòng `i` là `sq[i]`, đúng thứ tự nhập.

Không có tham số dòng lệnh, không dùng `fork`.

## Bài này để làm gì
Đây là bước khởi động cho `thread-echo`. Ở đó mỗi client một luồng, và điều nguy hiểm nhất là **cách đưa "việc của luồng"
(số `fd` của client) cho luồng**. Bài này luyện đúng phần đó, chưa có mạng:

| Kỹ thuật dùng ở `thread-echo` | Làm ở bài này |
|---|---|
| Hàm luồng có dạng `void *f(void *arg)` | Hàm `worker` tính bình phương |
| Đưa dữ liệu riêng cho từng luồng: `malloc` một ô nhớ cho mỗi luồng, luồng đọc xong thì `free` | Ô nhớ chứa **chỉ số `i`** của luồng |
| Không bao giờ truyền địa chỉ của biến vòng lặp (`&i`, `&client`) | Test 200 luồng bắt lỗi này |
| Biên dịch với `-pthread` (bộ chấm đã bật sẵn) | — |

(`thread-echo` dùng `pthread_detach` thay cho `pthread_join`. Server chạy mãi nên không có lúc nào "chờ mọi luồng xong".
Bài này cần in kết quả nên dùng `pthread_join`; phần `detach` nằm ở bài `thread-slow-hello`.)

## Ràng buộc
- `0 ≤ n ≤ 200`; `n = 0` thì không in gì. Mỗi `|a[i]| ≤ 10^9` (bình phương tới `10^18`: dùng `long long`).
- Phải tạo **đúng `n` luồng**, luồng `i` chỉ ghi vào `sq[i]`. Hàm `main` không được tự tính bình phương.
- Mảng `a[]`, `sq[]` là biến toàn cục (cả hai đều tới 200 phần tử). Mảng `pthread_t` cũng dùng được tới 200 phần tử.

## Ví dụ

```
stdin :  3          stdout:  9
         3                   16
         -4                  0
         0
```

## Gợi ý
- Mẫu cho một luồng (chép từ thẻ **Server đa luồng**):
  ```c
  void *worker(void *arg) {
      int i = *(int *)arg;     // lấy chỉ số ra
      free(arg);               // trả ô nhớ đã malloc
      sq[i] = a[i] * a[i];
      return NULL;
  }
  ...
  int *p = malloc(sizeof *p);  // một ô nhớ RIÊNG cho mỗi luồng
  *p = i;
  pthread_create(&tid[i], NULL, worker, p);
  ```
- Truyền `&i` (địa chỉ biến vòng lặp `for`) là sai: vòng lặp tăng `i` trước khi luồng mới kịp đọc, nên nhiều luồng cùng đọc
  một chỉ số, còn các ô còn lại không ai tính. Đây chính là lỗi trong `pthread_server.c` của thầy với `&client_socket`.
- Sau vòng tạo luồng, một vòng riêng `pthread_join(tid[i], NULL)` cho từng luồng rồi mới in. **Đừng** `join` ngay sau
  `pthread_create` trong cùng vòng lặp: các luồng sẽ chạy lần lượt, không còn song song.
