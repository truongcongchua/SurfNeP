// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen (như bài tcp-hello-loop)
    // TODO: vòng lặp vô hạn: accept; fopen(argv[2], "ab"); vòng recv + fwrite(đúng số byte nhận được) tới khi recv <= 0;
    //       fclose; close(client)
    return 0;
}
