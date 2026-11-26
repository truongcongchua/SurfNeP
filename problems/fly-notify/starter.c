// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, signal, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define MAX_CLIENTS 64
#define BUF_SIZE 2048

enum { ON_TIME, DELAYED, RESCHEDULED, CANCELLED };

typedef struct { char code[16]; int status, delay; char date[16], dep[8], arr[8]; } Flight;
// Hàng đợi thông báo theo tài khoản: mỗi phần tử một dòng "301 NOTIFY ...\n".
typedef struct { char user[40], pass[40]; char (*q)[128]; int nq, cap; } Account;
typedef struct { int acct, flight; } Ticket;   // chỉ các vé PAID
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int acct, admin; } Client;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <admin-key>\n", argv[0]);
        return 1;
    }
    // TODO (nên làm): signal(SIGPIPE, SIG_IGN)
    // TODO: nạp flights.txt, accounts.txt, tickets.txt (chỉ vé PAID)
    // TODO: server nhiều client; LOGIN (nhiều phiên cùng tài khoản được), ADMIN, STATUS, DELAY, RESCHEDULE, CANCELFLIGHT, QUIT
    // TODO: sự kiện: cập nhật trạng thái chuyến; với mỗi khách có vé PAID trên chuyến: gửi cho MỌI phiên đang online,
    //       nếu không có phiên nào thì xếp vào hàng đợi; sau "100 OK <user>" của LOGIN kế tiếp thì giao hàng đợi
    // TODO: gửi thông báo TRƯỚC khi trả "100 OK <k>" cho admin
    return 0;
}
