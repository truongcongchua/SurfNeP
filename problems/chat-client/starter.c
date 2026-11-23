// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket, sys/select)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket, inet_addr, connect như tcp_client.c (lỗi -> perror + thoát mã khác 0)
    // TODO: vòng lặp select() như select_client.c (FD_SET stdin và socket mỗi vòng, timeout NULL):
    //   - socket sẵn sàng: recv -> fwrite ra stdout + fflush; recv <= 0 -> đóng, thoát mã 0
    //   - stdin sẵn sàng: read(STDIN_FILENO, ...) -> send đúng số byte; read trả 0 (EOF) -> đóng, thoát mã 0
    return 0;
}
