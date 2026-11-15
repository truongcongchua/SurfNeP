// Harness của bộ chấm cho bài tcp-recv-line.
// stdin: dòng đầu "cap chunk delay_ms", phần còn lại là dữ liệu thô bên kia sẽ gửi.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

ssize_t recv_line(int fd, char *buf, size_t cap);

int main(void) {
    size_t cap, chunk;
    int delay;
    if (scanf("%zu %zu %d", &cap, &chunk, &delay) != 3) return 2;
    getchar();  // bỏ '\n' sau dòng đầu
    static char data[1 << 20];
    size_t len = fread(data, 1, sizeof data, stdin);

    int sv[2];
    socketpair(AF_UNIX, SOCK_STREAM, 0, sv);
    pid_t pid = fork();
    if (pid == 0) {  // phía gửi
        close(sv[0]);
        for (size_t i = 0; i < len; i += chunk) {
            size_t n = len - i < chunk ? len - i : chunk;
            if (write(sv[1], data + i, n) < 0) _exit(1);
            if (delay) usleep(delay * 1000);
        }
        close(sv[1]);
        _exit(0);
    }
    close(sv[1]);
    char *buf = malloc(cap + 16);
    for (int iter = 0; iter < 100000; iter++) {
        memset(buf, 'Z', cap + 16);
        ssize_t n = recv_line(sv[0], buf, cap);
        printf("%zd [", n);
        for (ssize_t i = 0; i < n && i < (ssize_t)cap; i++) {
            unsigned char ch = (unsigned char)buf[i];
            if (ch == '\n') fputs("\\n", stdout);
            else if (ch == '\r') fputs("\\r", stdout);
            else if (ch == 0) fputs("\\0", stdout);
            else putchar(ch);
        }
        printf("]");
        if (n >= 0 && (size_t)n < cap && buf[n] != 0) printf(" THIEU_NUL");
        if (n >= (ssize_t)cap) printf(" TRAN_BO_DEM");
        putchar('\n');
        if (n <= 0) break;
    }
    waitpid(pid, NULL, 0);
    return 0;
}
