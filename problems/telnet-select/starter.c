#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <sys/select.h>

// Gợi ý chia hàm: check_login(line) đọc accounts.txt; run_command(fd, cmd) chạy
// system("cmd > out_<id>.txt 2>&1"), đọc tệp, gửi "OUTPUT <n>
" + n byte.

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>
", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: vòng lặp select(); mỗi client: bộ đệm dòng + trạng thái đã đăng nhập
    return 0;
}
