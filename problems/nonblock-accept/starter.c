// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket, sys/ioctl)

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: ioctl(listener, FIONBIO, &io_mode) (xem non_blocking_server.c)
    // TODO: vòng lặp: thử accept (client mới cũng đặt FIONBIO); thử recv từng client:
    //       > 0 gửi lại, == 0 close và xoá khỏi mảng, == -1 bỏ qua
    return 0;
}
