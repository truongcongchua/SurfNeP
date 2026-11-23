// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <greeting_file> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: với mỗi client: fopen(argv[2], "rb") + vòng fread/send (như html.c), fclose;
    //       rồi fopen(argv[3], "ab"), vòng recv/fwrite tới khi recv <= 0, fclose, close(client)
    return 0;
}
