# Gửi dữ liệu từ bàn phím qua TCP

Viết chương trình **client** chạy bằng:

```
./tcp_client <địa chỉ IP> <cổng>
```

- Kết nối TCP tới server tại `<địa chỉ IP>:<cổng>`.
- Đọc dữ liệu từ bàn phím (stdin) và gửi tới server **ngay khi đọc được từng dòng**. Không được
  đợi đọc hết stdin rồi mới gửi.
- Khi stdin kết thúc (EOF, tức `Ctrl+D`): đóng kết nối và thoát với mã `0`.
- Nếu không kết nối được (sai địa chỉ, server không mở cổng): in thông báo lỗi ra `stderr` và
  thoát với mã **khác 0**, không treo.
- Dữ liệu gửi đi phải **giống hệt** dữ liệu nhập vào, kể cả ký tự xuống dòng.

## Bộ chấm kiểm tra
Bộ chấm dựng một server giả, chạy chương trình của bạn với tham số `127.0.0.1 <cổng>`, rồi ghi
vào stdin của nó. Server giả kiểm tra từng dòng có đến kịp thời hay không và toàn bộ dữ liệu có
khớp không.
