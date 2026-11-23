// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, unistd)

#define PHRASE "Ky thuat May tinh"

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen -> accept
    // TODO: recv trong vòng lặp, phát hiện PHRASE kể cả khi nó bị cắt thành nhiều mảnh
    return 0;
}
