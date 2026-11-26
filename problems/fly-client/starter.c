// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, unistd)

// Gợi ý: đọc stdin bằng read(STDIN_FILENO, ...) vào bộ đệm riêng rồi tự tách dòng. KHÔNG dùng fgets/scanf trộn với select:
// dữ liệu đã nằm trong bộ đệm của FILE thì select(stdin) không báo, và client sẽ treo.
static char rb[16384], ib[4096];       // bộ đệm socket và bộ đệm stdin
static size_t rlen, ilen;

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket + connect (lỗi -> in "Khong ket noi duoc", thoát mã 1); đọc dòng chào, "500..." -> "Server day: ..." mã 1
    // TODO: vòng lặp menu: in menu, chờ người dùng gõ lựa chọn
    // TODO: hàm "chờ một dòng người dùng" dùng select({stdin, socket}): socket có dữ liệu -> ghép dòng, "301 NOTIFY x" -> in "[THONG BAO] x"
    // TODO: hàm "chờ một dòng phản hồi" bỏ qua (và in) các thông báo xen giữa
    // TODO: chức năng 1-5 theo bảng trong đề (hỏi từng giá trị, gửi lệnh, in kết quả); BOOK thành công -> hỏi thanh toán
    // TODO: stdin EOF -> gửi QUIT, thoát mã 0; server đóng -> in "Mat ket noi", thoát mã 1
    return 0;
}
