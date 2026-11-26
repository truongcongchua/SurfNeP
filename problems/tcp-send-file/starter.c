// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, fcntl, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen (như bài tcp-hello-loop)
    // TODO: vòng lặp vô hạn: accept; open(argv[2], O_RDONLY); vòng read + send(đúng số byte read trả về) tới khi read <= 0;
    //       close(fd); close(client)
    return 0;
}
