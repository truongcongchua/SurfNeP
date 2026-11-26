// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, signal, stdio, stdlib, string, sys/select, sys/socket, sys/stat, unistd)

#define MAX_CLIENTS 64
#define BUF_SIZE 2048

typedef struct { char user[40], pass[40], email[80]; } Account;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;   // acct = -1: chưa đăng nhập

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <smtp-ip> <smtp-port>\n", argv[0]);
        return 1;
    }
    // TODO (tùy chọn nhưng nên làm): signal(SIGPIPE, SIG_IGN)
    // TODO: nạp accounts.txt (user pass email); đếm số dòng tickets.txt để biết số thứ tự vé tiếp theo
    // TODO: server nhiều client; LOGIN (nhiều phiên cùng tài khoản được), ISSUE, QUIT
    // TODO: ISSUE: số vé 13 chữ số, ghi nối tickets.txt, gửi email qua SMTP (HELO/MAIL/RCPT/DATA/.), lưu outbox/<user>/<số vé>.eml,
    //       đẩy "300 TICKET <số vé>" cho các phiên khác cùng tài khoản, rồi trả "100 OK <số vé>[ MAIL_FAILED]"
    // TODO: SMTP: chờ phản hồi bằng select có timeout 2s; phản hồi nhiều dòng "250-..." đọc đến dòng "250 ..."
    return 0;
}
