// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, sys/socket, unistd)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket(AF_INET, SOCK_DGRAM, 0) -> bind
    // TODO: phân tích "<a> <op> <b>" / "COUNT"; bộ đếm theo từng người gửi
    return 0;
}
