// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket, sys/select)

#define BUF_SIZE 4096

// Gợi ý: dùng select() như select_server.c (hoặc pthread); mỗi client một bộ đệm dòng riêng.
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; } Client;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <N>\n", argv[0]);
        return 1;
    }
    int limit = atoi(argv[2]);
    (void)limit;
    // TODO: socket -> bind -> listen
    // TODO: accept: còn chỗ -> WELCOME, hết chỗ -> FULL rồi close
    // TODO: ghép dòng cho từng client; COUNT / QUIT / ECHO <dòng>
    return 0;
}
