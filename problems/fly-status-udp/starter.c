// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, unistd)

#define MAX_FLIGHTS 1000
#define MAXLEN 1000

// Gợi ý: mỗi cặp (mã chuyến, ngày) trong flights.txt là một Entry.
typedef struct {
    char code[16], date[16];
    int state;  // 0 = ON_TIME, 1 = DELAYED, 2 = CANCELLED
    int minutes;
} Entry;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <key>\n", argv[0]);
        return 1;
    }
    // TODO: nạp flights.txt (chỉ cần cột mã chuyến và ngày)
    // TODO: socket(AF_INET, SOCK_DGRAM, 0) -> bind; vòng lặp recvfrom
    // TODO: kiểm tra độ dài, bỏ "\n" rồi "\r" cuối, tách theo đúng một dấu cách
    // TODO: STATUS / SET theo đề; sendto về đúng địa chỉ người gửi
    return 0;
}
