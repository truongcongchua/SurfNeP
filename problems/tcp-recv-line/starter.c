#include <sys/socket.h>
#include <sys/types.h>

// Không viết main(): bộ chấm có main riêng gọi hàm này.
ssize_t recv_line(int fd, char *buf, size_t cap) {
    // TODO
    (void)fd; (void)buf; (void)cap;
    return -1;
}
