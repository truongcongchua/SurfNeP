// TODO: tự #include các thư viện cần dùng (gợi ý: stdio, stdlib, string, unistd, time, arpa/inet, sys/socket)

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <port> <log_file>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen; accept lấy cả địa chỉ client, IP bằng inet_ntoa (như udp_receiver.c)
    // TODO: đọc từng bản ghi theo đúng định dạng: lặp recv tới khi đủ số byte của từng phần,
    //       giải mã bằng memcpy + ntohl/ntohs, kiểm tra hợp lệ
    // TODO: hợp lệ -> printf + fflush(stdout), ghi nối tiếp vào log (fopen "a", fclose), gửi "OK\n";
    //       không hợp lệ -> gửi "ERROR\n" rồi đóng kết nối
    // Lấy thời gian hiện tại (chép nguyên đoạn này):
    //     char now[32];
    //     time_t t = time(NULL);
    //     strftime(now, sizeof(now), "%Y-%m-%d %H:%M:%S", localtime(&t));
    return 0;
}
