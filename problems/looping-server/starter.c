// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, sys/stat, unistd)

#define REQ_MAX 8192

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <port> <root_dir>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp: accept -> đọc yêu cầu đến khi có dòng trống -> phân tích dòng đầu
    //       -> trả 200/400/403/404/405 với đúng 4 header -> close
    return 0;
}
