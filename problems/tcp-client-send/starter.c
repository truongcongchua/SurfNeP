// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <ip> <port> <message>\n", argv[0]);
        return 1;
    }
    // TODO: socket, inet_addr(argv[1]), htons(atoi(argv[2])), connect như tcp_client.c
    //       (connect lỗi -> perror + thoát mã khác 0)
    // TODO: send(argv[3], strlen(argv[3])) rồi send("\n", 1); xong thì close + return 0
    return 0;
}
