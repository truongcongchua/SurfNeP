// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, unistd, arpa/inet, sys/socket, sys/select)

#define MAX_CLIENTS 512

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> setsockopt(SO_REUSEADDR) -> bind -> listen(.., 64)
    int client_list[MAX_CLIENTS];
    int number_of_clients = 0;
    while (1) {
        // TODO: FD_ZERO, FD_SET listener và mọi client trong client_list, tính max_fd
        // TODO: select(max_fd + 1, ...)
        // TODO: FD_ISSET(listener) -> accept, thêm vào client_list, gửi "ONLINE <số client hiện có>\n"
        // TODO: client nào FD_ISSET -> recv và bỏ dữ liệu; recv <= 0 -> close và xoá khỏi client_list
    }
    return 0;
}
