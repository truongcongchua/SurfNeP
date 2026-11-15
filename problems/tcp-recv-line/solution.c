#include <sys/socket.h>
#include <sys/types.h>

ssize_t recv_line(int fd, char *buf, size_t cap) {
    if (cap == 0) return -1;
    size_t n = 0;
    while (n + 1 < cap) {
        char ch;
        ssize_t k = recv(fd, &ch, 1, 0);
        if (k < 0) return -1;
        if (k == 0) break;
        buf[n++] = ch;
        if (ch == '\n') break;
    }
    buf[n] = 0;
    return (ssize_t)n;
}
