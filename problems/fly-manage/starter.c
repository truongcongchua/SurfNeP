// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, signal, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define MAX_CLIENTS 64
#define BUF_SIZE 2048

typedef struct { char code[16], from[8], to[8], date[16], dep[8], arr[8]; long long price[2]; int seats[2]; } Flight;   // [0] = ECO, [1] = BUS
typedef struct { char user[40], pass[40]; long long balance; } Account;
typedef struct { char no[20]; int acct, flight, cls, cancelled; char pax[48]; long long price; } Ticket;
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct; } Client;

// Gợi ý: đổi "YYYY-MM-DD HH:MM" ra số phút kể từ một mốc cố định (mktime hoặc công thức ngày dân sự),
// rồi mọi phép "còn lại bao lâu" chỉ là phép trừ hai số nguyên.
// static long long to_minutes(const char *date, const char *hhmm);

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <YYYY-MM-DD> <HH:MM>\n", argv[0]);
        return 1;
    }
    // TODO: nạp flights.txt, accounts.txt, wallets.txt, tickets.txt
    // TODO: server nhiều client; LOGIN / SEATS / BALANCE / MYTICKETS / VIEW / CANCEL / CHANGE / PRINT / QUIT theo đề
    // TODO: CANCEL: hoàn 90% / 70% / 30% theo số phút còn lại; CHANGE: chênh lệch có phí; PRINT: "120 FILE n" + đúng n byte
    return 0;
}
