// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket, inet_addr, connect như tcp_client.c (lỗi -> perror + thoát mã khác 0)
    // TODO: lặp: fgets 4 dòng (MSSV, họ tên, ngày sinh, điểm), bỏ "\r\n" cuối bằng strcspn; EOF -> thoát
    // TODO: sscanf từng trường; ghép bản ghi vào mảng unsigned char (htonl/htons + memcpy), send một lần
    // TODO: recv từng byte tới '\n' để lấy một dòng phản hồi, printf ra stdout; "ERROR" -> dừng
    return 0;
}
