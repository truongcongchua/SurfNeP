// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket, sys/select)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: inet_addr(argv[1]) (INADDR_NONE -> stderr + return 1); socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    // TODO: với mỗi dòng stdin: bỏ \r\n cuối (strcspn); dòng rỗng -> bỏ qua; sendto cả dòng
    // TODO: select() với timeout 1 giây (đặt lại mỗi lần, xem select_client.c);
    //       có dữ liệu -> recvfrom, fwrite đúng k byte + "\n"; không -> in "TIMEOUT\n"
    return 0;
}
