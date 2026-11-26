// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, fcntl, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <greeting_file> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: với mỗi client: open(argv[2], O_RDONLY) + vòng read/send tới khi read <= 0, close(fd);
    //       rồi open(argv[3], O_WRONLY | O_CREAT | O_APPEND, 0644), vòng recv/write tới khi recv <= 0,
    //       close(fd), close(client)
    return 0;
}
