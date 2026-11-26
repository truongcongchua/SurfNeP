// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, pthread, stdio, stdlib, string, strings, sys/socket, unistd)

#define MAX_FLIGHTS 1000
#define HEAD_MAX 8192

typedef struct {
    char code[16], airline[8], from[8], to[8], date[16], dep[8], arr[8];
    long long price[2];   // [0] = ECO, [1] = BUS
    int seats[2];
} Flight;

// Gợi ý như http_server.c: mỗi kết nối một luồng; truyền cho luồng một con trỏ int mới cấp phát (không truyền &biến của vòng accept).
// void *serve(void *arg): đọc đến "\r\n\r\n" -> sscanf method/target/version -> định tuyến -> gửi header đủ 4 dòng + thân -> close.

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: nạp flights.txt; socket lắng nghe; accept lặp, pthread_create + pthread_detach
    // TODO: GET / | GET /search?query | POST /search (đọc đủ Content-Length) | GET /flight/<mã>; 400 / 404 / 405 theo đề
    // TODO: giải mã %XX và '+' ; kiểm tra tham số như bài fly-parse ; HTML đúng các chuỗi mà đề nêu
    return 0;
}
