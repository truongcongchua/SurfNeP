// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, signal, arpa/inet, sys/socket, sys/types, sys/wait)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: signal(SIGCHLD, handler) với handler gọi waitpid(-1, NULL, WNOHANG) trong vòng while
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp accept -> fork; con: close(listener), echo, close(client), exit(0); cha: close(client)
    return 0;
}
