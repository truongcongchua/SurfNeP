// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> setsockopt(SO_REUSEADDR) -> bind -> listen (xem 2-Chap2/tcp_server.c)
    // TODO: vòng lặp accept; với mỗi client: recv rồi send lại đúng số byte nhận được,
    //       cho đến khi recv trả về <= 0; sau đó close(client) và accept client tiếp theo
    return 0;
}
