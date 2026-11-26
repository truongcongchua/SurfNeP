// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, time, unistd)

#define BUF_SIZE 2048
#define MAX_BOOKINGS 20000

enum { HOLD, PAID, EXPIRED, GONE };

typedef struct { char code[16], date[16]; long long price[2]; int seats[2]; } Flight;        // [0] = ECO, [1] = BUS
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct {
    char pnr[8];
    int acct, flight, cls, pax, state, sid;   // sid: phiên đã đặt (để trả chỗ giữ khi phiên rời đi)
    long long amount;
    time_t expire;
} Booking;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; int sid; } Client;

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <N> <T>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]), hold_secs = atoi(argv[3]);
    (void)limit; (void)hold_secs;
    // TODO: nạp flights.txt, accounts.txt, wallets.txt
    // TODO: socket lắng nghe; "100 OK WELCOME" / "500 FULL"; phục vụ nhiều client (select hoặc pthread + mutex)
    // TODO: LOGIN / SEATS / BALANCE / BOOK / PAY / RELEASE / QUIT theo đề
    // TODO: chỗ giữ hết hạn sau T giây (so sánh time(NULL) với b->expire ở đầu MỌI lệnh, hoặc dùng timeout của select)
    // TODO: client rời đi -> trả ghế của các chỗ giữ chưa thanh toán do phiên đó đặt
    return 0;
}
