// Tên verdict và lời giải thích ngắn bằng tiếng Việt (dùng được ở cả Server lẫn Client Component).
export const VERDICT_LABEL = {
  AC: "Accepted", WA: "Wrong Answer", CE: "Compile Error", RE: "Runtime Error", TLE: "Time Limit Exceeded", OLE: "Output Limit Exceeded",
  NL: "Not Listening", BLOCKED: "Blocked", LIMIT: "Client Limit", CV: "Constraint Violation", IE: "Internal Error",
};

// Nguyên nhân thường gặp của từng verdict trong các bài lập trình mạng.
export const VERDICT_HELP = {
  WA: "Chương trình chạy được nhưng kết quả khác đáp án. Với bài mạng, nguyên nhân phổ biến là giả định một `send` = một `recv` (không ghép dòng / không đọc đủ byte), quên đổi byte order, hoặc dùng `strlen` với dữ liệu nhị phân.",
  CE: "Mã nguồn không biên dịch được. Đọc dòng lỗi đầu tiên của gcc; hay gặp: thiếu `#include`, quên `-pthread` với luồng, sai kiểu con trỏ khi ép `sockaddr`.",
  RE: "Chương trình bị lỗi khi chạy (segfault, thoát bất thường). Kiểm tra truy cập mảng/con trỏ, bộ đệm tràn, và việc server thoát sau khi phục vụ một client.",
  TLE: "Chương trình không trả lời kịp thời gian. Thường do vòng lặp không kết thúc (quên xử lý `recv == 0`), `recv` chặn mãi vì đợi thêm dữ liệu không bao giờ đến, hoặc chờ sai kiểu (UDP không có EOF).",
  OLE: "Chương trình in quá nhiều dữ liệu, thường do vòng lặp vô hạn khi `recv` trả `0`/`-1` mà không thoát.",
  NL: "Bộ chấm không kết nối được tới cổng của bạn. Kiểm tra: đã `bind`/`listen` đúng cổng lấy từ `argv[1]` (nhớ `htons`), có `SO_REUSEADDR`, và chương trình có thoát sớm không.",
  BLOCKED: "Server bị chặn: một client treo/chậm làm client khác không được phục vụ. Kiểm tra `recv`/`accept` blocking trong vòng lặp chính, `pthread_join` ngay sau khi tạo luồng, hoặc cha `wait` con.",
  LIMIT: "Giới hạn số client tối đa N không đúng: kiểm tra điều kiện từ chối (`nclients >= N`), gửi đúng thông báo, và giảm bộ đếm ở **mọi** đường client rời đi.",
  CV: "Vi phạm ràng buộc của đề: bạn đã dùng hàm bị cấm (ví dụ `select` trong bài `poll`, `pthread` trong bài `select`) hoặc thiếu hàm bắt buộc. Đọc lại phần 'Không được dùng' trong đề.",
  IE: "Lỗi hệ thống chấm bài, không phải lỗi của bạn. Thử nộp lại sau.",
};
