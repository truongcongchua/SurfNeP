// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket, inet_addr(argv[1]), connect như tcp_client.c (lỗi -> perror + thoát mã khác 0)
    // TODO: lặp read(STDIN_FILENO, ...) rồi send đúng số byte đọc được; read trả 0 (EOF) -> close + return 0
    return 0;
}
