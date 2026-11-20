#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>

// Gợi ý chia hàm: check_login(line) đọc accounts.txt; run_command(fd, cmd) chạy
// system("cmd > out_<id>.txt 2>&1"), đọc tệp, gửi "OUTPUT <n>\n" + n byte.

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: SIGCHLD + waitpid; accept -> fork; trong con: signal(SIGCHLD, SIG_DFL) rồi phục vụ phiên
    return 0;
}
