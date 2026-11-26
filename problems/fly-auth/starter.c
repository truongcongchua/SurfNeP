// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define MAX_ACCOUNTS 1000
#define BUF_SIZE 2048

typedef struct { char user[40], pass[40]; } Account;

// Gợi ý: acct = chỉ số tài khoản đang đăng nhập của phiên này, -1 nếu chưa đăng nhập.
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    (void)limit;
    // TODO: nạp accounts.txt (fopen + fscanf/fgets)
    // TODO: socket lắng nghe; "100 OK WELCOME" hoặc "500 FULL" theo giới hạn N
    // TODO: ghép dòng cho từng client; REGISTER / LOGIN / LOGOUT / WHOAMI / QUIT theo đề
    // TODO: REGISTER thành công phải ghi nối vào accounts.txt ngay (fopen "a", fprintf, fclose)
    return 0;
}
