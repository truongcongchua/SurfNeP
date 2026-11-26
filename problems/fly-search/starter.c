// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define MAX_FLIGHTS 1000
#define BUF_SIZE 2048

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long eco_price, bus_price;
    int eco_seats, bus_seats;
} Flight;

// Gợi ý: mỗi client một bộ đệm dòng riêng (giống kv-max-n).
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: nạp flights.txt một lần (fopen + fgets + sscanf, như bài flight-filter)
    // TODO: socket lắng nghe; phục vụ nhiều client (select hoặc pthread)
    // TODO: ghép dòng; SEARCH / QUIT / lệnh lạ theo đề; kiểm tra cú pháp như bài fly-parse
    return 0;
}
