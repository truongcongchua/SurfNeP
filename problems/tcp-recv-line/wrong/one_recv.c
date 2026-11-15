// SAI có chủ đích: một lần recv rồi cắt ở '\n' -> mất phần sau và hỏng khi dòng bị cắt vụn.
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>

ssize_t recv_line(int fd, char *buf, size_t cap) {
    ssize_t n = recv(fd, buf, cap - 1, 0);
    if (n <= 0) { buf[0] = 0; return n; }
    char *nl = memchr(buf, '\n', (size_t)n);
    if (nl) n = nl - buf + 1;
    buf[n] = 0;
    return n;
}
