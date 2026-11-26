// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define BUF_SIZE 2048

typedef struct { char code[16], from[8], to[8], date[16], dep[8], arr[8]; long long price; int seats; } Flight;
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct { int id, acct, flight, alive; } Ticket;      // acct = chỉ số tài khoản đã mua
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;   // acct = -1: chưa LOGIN

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    (void)limit;
    // TODO: nạp flights.txt, accounts.txt, wallets.txt
    // TODO: socket lắng nghe; WELCOME / FULL theo giới hạn N
    // TODO: ghép dòng cho từng client; LOGIN / SEARCH / BOOK / MYTICKETS / CANCEL / BALANCE / QUIT theo đề
    return 0;
}
