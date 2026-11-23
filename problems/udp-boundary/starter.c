// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, sys/socket, unistd)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket(AF_INET, SOCK_DGRAM, 0) -> bind
    // TODO: bộ đệm đủ 65507 byte; bảng (IP, cổng) -> số thứ tự; trả lời "LEN <n> <thứ tự>"
    return 0;
}
