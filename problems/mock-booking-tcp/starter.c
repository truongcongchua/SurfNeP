// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, unistd)

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <port> <N> <S>\n", argv[0]);
        return 1;
    }
    // Tự chọn kỹ thuật (select / pthread + mutex) và tự thiết kế cấu trúc dữ liệu.
    return 0;
}
