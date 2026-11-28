// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, unistd, arpa/inet, sys/socket, sys/select)

int make_listener(int port) {
    // TODO: socket -> setsockopt(SO_REUSEADDR) -> bind -> listen(.., 64), trả về fd
    return -1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    int port = atoi(argv[1]);
    int listener1 = make_listener(port);
    int listener2 = make_listener(port + 1);
    fd_set read_fds;
    while (1) {
        // TODO: FD_ZERO, FD_SET cả hai listener, max_fd = lớn nhất của hai fd
        // TODO: select(max_fd + 1, &read_fds, NULL, NULL, NULL)
        // TODO: FD_ISSET(listener1) -> accept, send "ONE\n", close client
        // TODO: FD_ISSET(listener2) -> accept, send "TWO\n", close client
    }
    return 0;
}
