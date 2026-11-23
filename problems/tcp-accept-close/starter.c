// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO 1: socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) -> listener (lỗi: perror + exit)
    // TODO 2: điền struct sockaddr_in (sin_family, sin_port = htons(atoi(argv[1])), INADDR_ANY) rồi bind
    // TODO 3: listen(listener, 5)
    // TODO 4: client = accept(listener, NULL, NULL)
    // TODO 5: close(client); close(listener); return 0
    return 0;
}
