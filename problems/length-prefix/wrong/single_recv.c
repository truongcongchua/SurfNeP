// SAI có chủ đích: giả định một recv() nhận trọn một thông điệp.
#include <arpa/inet.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(atoi(argv[1]));
    bind(ls, (struct sockaddr *)&a, sizeof a);
    listen(ls, 5);
    static unsigned char buf[70000];
    for (;;) {
        int c = accept(ls, NULL, NULL);
        ssize_t n;
        while ((n = recv(c, buf, sizeof buf, 0)) >= 4) {
            uint32_t len;
            memcpy(&len, buf, 4);
            len = ntohl(len);
            if (len > 65536) break;
            for (uint32_t i = 4; i < 4 + len && i < (uint32_t)n; i++)
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
            send(c, buf, 4 + len, 0);
        }
        close(c);
    }
}
