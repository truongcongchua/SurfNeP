// TODO: tự #include các thư viện cần dùng (gợi ý: arpa/inet, stdio, stdlib, string, sys/socket, unistd, signal, sys/wait)

// Gợi ý chia hàm: check_login(line) đọc accounts.txt; run_command(fd, cmd) chạy
// system("cmd > out_<id>.txt 2>&1"), đọc tệp, gửi "OUTPUT <n>\n" + n byte.

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen
    // TODO: signal(SIGCHLD, handler) với waitpid trong vòng while; accept -> fork; con phục vụ phiên rồi exit
    return 0;
}
