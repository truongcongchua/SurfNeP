// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, pthread, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp accept -> malloc một int chứa fd -> pthread_create(..., handle_client, arg) -> pthread_detach
    // TODO: handle_client: lấy fd, free(arg), echo cho tới khi recv <= 0, close
    return 0;
}
