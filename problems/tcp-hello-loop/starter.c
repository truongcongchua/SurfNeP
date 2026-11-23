// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen (làm như bài tcp-accept-close)
    // TODO: int count = 0;  (khai báo NGOÀI vòng lặp)
    // TODO: vòng lặp vô hạn: accept -> count++ -> sprintf(message, "Hello, client %d!\n", count)
    //       -> send(client, message, strlen(message), 0) -> close(client)
    return 0;
}
