// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, time, unistd)

#define MAX_CLIENTS 64
#define BUF_SIZE 2048

// Gợi ý: lưu sẵn địa chỉ "ip:cổng" của mỗi client (lấy từ accept) để ghi log.
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; char addr[32]; } Client;

// Gợi ý: một hàm ghi log dùng chung, nhận loại sự kiện (CONNECT/RECV/SEND/DISCONNECT) và nội dung.
static FILE *logf;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <logfile>\n", argv[0]);
        return 1;
    }
    // TODO: mở tệp log chế độ "a" một lần
    // TODO: socket lắng nghe; accept(ls, (struct sockaddr *)&ca, &len) rồi inet_ntoa / ntohs để lấy địa chỉ client
    // TODO: ghép dòng cho từng client; PING / QUIT / lệnh lạ theo đề
    // TODO: mỗi sự kiện một dòng log "[giờ] KIND addr \"text\"", fflush ngay, ghi SEND TRƯỚC khi gửi
    return 0;
}
