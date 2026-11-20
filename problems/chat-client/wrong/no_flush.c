#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
// SAI có chủ đích: in bằng stdio không fflush -> stdout (tệp/pipe) được đệm đầy, tin hiện quá muộn.

static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
}

static void write_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = write(fd, buf, n);
        if (k <= 0) return;
        buf += k;
        n -= (size_t)k;
    }
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in sa = {0};
    sa.sin_family = AF_INET;
    sa.sin_port = htons((unsigned short)atoi(argv[2]));
    if (inet_pton(AF_INET, argv[1], &sa.sin_addr) != 1) {
        fprintf(stderr, "dia chi IP khong hop le: %s\n", argv[1]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (connect(s, (struct sockaddr *)&sa, sizeof sa) < 0) {
        perror("connect");
        return 1;
    }
    struct pollfd fds[2] = {{.fd = 0, .events = POLLIN}, {.fd = s, .events = POLLIN}};
    char buf[4096];
    for (;;) {
        if (poll(fds, 2, -1) < 0) continue;
        if (fds[0].revents & (POLLIN | POLLHUP)) {
            ssize_t k = read(0, buf, sizeof buf);
            if (k > 0) {
                if (send_all(s, buf, (size_t)k) < 0) return 0;
            } else {  // EOF: không gửi nữa nhưng vẫn nhận tiếp
                shutdown(s, SHUT_WR);
                fds[0].fd = -1;  // poll bỏ qua fd âm
            }
        }
        if (fds[1].revents & (POLLIN | POLLHUP | POLLERR)) {
            ssize_t k = recv(s, buf, sizeof buf, 0);
            if (k <= 0) return 0;
            fwrite(buf, 1, (size_t)k, stdout);  // SAI: không fflush, stdout là tệp nên chỉ hiện khi thoát
        }
    }
}
