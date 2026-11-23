// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket, sys/select)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp select() (xem select_server.c): dựng lại fd_set mỗi vòng, accept client mới,
    //       recv rồi send lại cho client có dữ liệu; recv <= 0 thì close và xoá khỏi danh sách
    return 0;
}
