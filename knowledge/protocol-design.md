---
title: "Thiết kế giao thức tự định nghĩa (BTL đặt vé máy bay)"
chapter: 4
ref: "Lecture notes §4.1–4.3; giao thức chat §4.3; 4-Chap4/pthread_chatroom.c"
---

## Giao thức là gì
**Giao thức** là tập quy ước mà client và server cùng tuân theo để hiểu nhau: *thông điệp trông thế nào*, *ai nói
trước*, *mỗi thông điệp được trả lời ra sao*. Bài giảng §4.3 liệt kê **6 câu hỏi** phải trả lời khi thiết kế:

| Câu hỏi | Lựa chọn của giao thức FLY (BTL đặt vé) |
|---|---|
| Thông điệp text hay binary? | **Text**, mỗi thông điệp một dòng kết thúc `\n` |
| Server bị động hay chủ động? | Chủ yếu bị động (đáp lệnh), nhưng **chủ động đẩy** vé điện tử và thông báo chuyến bay |
| Xử lý từng yêu cầu hay nhiều? | Lần lượt từng dòng, nhiều dòng có thể dính nhau trong một `recv` |
| Có làm việc theo phiên không? | **Có**: mỗi kết nối nhớ đã đăng nhập chưa (và là ai) |
| Xác thực thế nào? | `LOGIN user pass` đối chiếu `accounts.txt` |
| Có bảo mật không? | Không (mật khẩu đi dạng rõ; mã hóa là Chương 5) |

## Định dạng lệnh và phản hồi
Giao thức chat trong bài giảng dùng **mã trạng thái ba chữ số** (`100 OK`, `200 NICKNAME IN USE`, `999 UNKNOWN ERROR`)
giống HTTP (§4.2.1: 2xx thành công, 4xx lỗi client, 5xx lỗi server). Bộ bài FLY theo cùng kiểu:

| Mã | Ý nghĩa |
|---|---|
| `100 OK ...` | thành công |
| `110 FLIGHTS k` + `k` dòng, `111 RETURN m` + `m` dòng | phản hồi **nhiều dòng**, đếm trước |
| `120 FILE n` + đúng `n` byte | gửi nội dung có độ dài (vé để in) |
| `200`–`209` | lỗi của client: tên đã dùng, sai cú pháp, không thấy, bị từ chối, chưa đăng nhập, hết ghế, thanh toán lỗi, đã trả, hết hạn |
| `3xx` | server **chủ động** gửi (vé điện tử, thông báo) |
| `500 FULL` | đủ `N` client |
| `999 UNKNOWN ERROR` | lệnh lạ |

## Vì sao phải "đếm trước"?
TCP là luồng byte: client không thể đoán phản hồi dài bao nhiêu. Có ba cách để biết **hết** dữ liệu:
1. **Đếm trước** số dòng hoặc số byte (`110 FLIGHTS 3`, `120 FILE 512`): đơn giản và chắc nhất, giống `OUTPUT <n>` của telnet.
2. **Dòng kết thúc** đặc biệt (như dấu `.` của POP3/SMTP).
3. Đóng kết nối (HTTP/1.0): mỗi lần chỉ phục vụ được một yêu cầu.

## Tách lệnh bằng đúng một dấu cách
```c
char *tok[16]; int nt = 0;
for (char *p = line;;) {
    tok[nt++] = p;                       // nhớ đầu thành phần
    char *sp = strchr(p, ' ');
    if (!sp) break;
    *sp = 0;                             // cắt thành phần
    p = sp + 1;                          // sang thành phần kế
}
```
`strtok(line, " ")` **không dùng được** khi dấu cách thừa là lỗi: nó coi nhiều dấu cách liền nhau là một và làm mất
thành phần rỗng. Sau khi tách phải kiểm tra **số thành phần** trước, rồi mới kiểm tra nội dung từng thành phần.

## Kiểm tra nội dung: ngày và số thẻ
- Ngày `YYYY-MM-DD` có thật: tháng 1–12, ngày ≤ số ngày của tháng; năm nhuận khi chia hết cho 4 **và** không chia hết
  cho 100, trừ khi chia hết cho 400 (1900 và 2100 không nhuận, 2000 nhuận).
- So sánh ngày dạng `YYYY-MM-DD` bằng `strcmp` là đúng (so từ trái sang phải đúng thứ tự thời gian).
- Số thẻ mô phỏng: 16 chữ số **và** thuật toán Luhn (từ phải sang trái, nhân đôi chữ số ở vị trí lẻ, trừ 9 nếu lớn hơn 9,
  tổng chia hết cho 10). Thanh toán trong bài chỉ là mô phỏng, không có cổng thanh toán thật.

## Thông điệp server chủ động gửi
Server không chỉ đáp lệnh: khi có sự kiện (chuyến bị hủy, vé đã phát hành) nó gửi thẳng cho client liên quan. Với
`select` hoặc luồng, việc cần làm là duyệt danh sách client (như hàm phát tin của phòng chat) và `send` tới đúng người.
Client phải chấp nhận dòng `3xx` **xen vào bất kỳ lúc nào**, kể cả giữa lúc đang đọc một phản hồi nhiều dòng của
lệnh khác (khi đó nên gom thông báo lại và hiển thị sau).

## Thứ tự kiểm tra lỗi
Khi một lệnh có thể sai theo nhiều cách, **đề phải ghi rõ thứ tự kiểm tra** vì client chỉ thấy một mã lỗi. Ví dụ `PAY`:
đăng nhập → cú pháp → PNR có tồn tại → của đúng người → đã trả chưa → hết hạn chưa → thanh toán. Lời giải nên kiểm tra theo
đúng thứ tự đó, không theo thứ tự tiện viết.

## Dữ liệu dùng chung giữa nhiều client
Danh sách ghế, ví, vé phải dùng chung: với `select` (một luồng) không cần khóa; với đa luồng mọi truy cập vào dữ liệu
chung phải nằm trong `pthread_mutex_lock` … `pthread_mutex_unlock`; `fork` **không dùng được** vì mỗi tiến trình con có
bản sao riêng. Mẫu lỗi kinh điển: kiểm tra "còn ghế" rồi mới trừ ghế ở hai bước tách rời khi hai client cùng xen vào.

## Giữ chỗ có hạn
Giữ ghế rồi tự trả nếu không thanh toán kịp là bài toán **thời gian**. Cách đơn giản nhất: lưu `hết_hạn = time(NULL) + T`
trong bản ghi, và ở **đầu mỗi lệnh** quét các bản ghi `HOLD` có `hết_hạn <= time(NULL)` rồi trả ghế (xét "lười"). Kết hợp
timeout của `select` (`struct timeval`) nếu muốn dọn cả khi không ai gửi lệnh. `time`, `localtime`, `strftime` là thư
viện C chung, không thuộc lập trình mạng nên được dùng thoải mái.

## Bẫy hay gặp
- Gọi `recv` một lần rồi coi cả bộ đệm là **một** lệnh (code mẫu `pthread_chatroom.c` mắc lỗi này): phải ghép dòng.
- Truyền `&client_socket` (biến cục bộ của vòng `accept`) cho luồng: vòng sau ghi đè giá trị. Hãy cấp phát riêng hoặc
  truyền giá trị.
- `sscanf("%s")` vào mảng cố định: giới hạn độ rộng (`%63s`).
- Quên trả lại tài nguyên khi client rời đi (ghế đang giữ, tài khoản đang đăng nhập, chỗ trong giới hạn `N`).
