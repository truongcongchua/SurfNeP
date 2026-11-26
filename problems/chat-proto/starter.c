// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/select, sys/socket, unistd)

#define MAX_CLIENTS 64
#define BUF_SIZE 4096

// Gợi ý: giống pthread_chatroom.c — mỗi client có nickname; thêm bộ đệm dòng riêng và cờ đã JOIN.
typedef struct { int fd; char buf[BUF_SIZE]; size_t len; int joined; char nick[40]; } Client;

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket lắng nghe; phục vụ nhiều client (select hoặc pthread + mutex)
    // TODO: ghép dòng; tách lệnh ở dấu cách đầu tiên (tên lệnh / tham số nguyên văn)
    // TODO: JOIN / MSG / PMSG / QUIT theo đề; hàm tìm client theo nick (như get_nickname)
    return 0;
}
