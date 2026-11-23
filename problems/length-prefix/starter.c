// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

#define MAX_LEN 65536

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen; vòng lặp accept (như tcp_server.c)
    // TODO: mỗi client, lặp:
    //   - gọi recv nhiều lần cho tới khi đủ 4 byte độ dài; ntohl -> L (unsigned int); L > 65536 thì đóng
    //   - gọi recv nhiều lần cho tới khi đủ L byte dữ liệu
    //   - đổi a-z thành A-Z, send lại 4 byte độ dài rồi L byte dữ liệu
    return 0;
}
