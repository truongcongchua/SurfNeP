// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, unistd)

int main(int argc, char *argv[]) {
    if (argc != 7) {
        fprintf(stderr, "Usage: %s <ip> <port> <user> <pass> <ticket> <outfile>\n", argv[0]);
        return 1;
    }
    // TODO: socket + connect như tcp_client.c (lỗi -> perror, thoát mã 1)
    // TODO: hàm read_line dùng bộ đệm GIỮ giữa các lần gọi (phần dữ liệu thừa sau dòng tiêu đề là nội dung vé!)
    // TODO: chờ "100 OK WELCOME" -> gửi "LOGIN user pass" -> chờ "100 ..." -> gửi "PRINT ticket" -> chờ "120 FILE n"
    // TODO: n hợp lệ (số thập phân, 0..5000000); nhận đúng n byte, ghi bằng fwrite (không strlen/fputs); không cấp phát theo n
    // TODO: lỗi: in "ERROR <dòng server>", gửi QUIT, thoát mã 1 và không để lại tệp ra
    // TODO: thành công: gửi "QUIT", đóng kết nối, thoát mã 0
    return 0;
}
