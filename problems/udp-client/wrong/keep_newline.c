// SAI có chủ đích: không bỏ ký tự xuống dòng cuối dòng nên datagram thừa một byte.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[2]));
    addr.sin_addr.s_addr = inet_addr(argv[1]);
    if (addr.sin_addr.s_addr == INADDR_NONE) {
        fprintf(stderr, "dia chi IP khong hop le: %s\n", argv[1]);
        return 1;
    }
    int sender_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    char line[4096], reply[2049];
    while (fgets(line, sizeof(line), stdin) != NULL) {
        int n = strlen(line);
        if (n == 0) continue;
        sendto(sender_socket, line, n, 0, (struct sockaddr *)&addr, sizeof(addr));

        // Đợi phản hồi tối đa 1 giây. select() có thể sửa timeout nên phải đặt lại mỗi lần.
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(sender_socket, &read_fds);
        struct timeval timeout;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;
        int activity = select(sender_socket + 1, &read_fds, NULL, NULL, &timeout);
        if (activity > 0) {
            int k = recvfrom(sender_socket, reply, sizeof(reply) - 1, 0, NULL, NULL);
            if (k >= 0) {
                fwrite(reply, 1, k, stdout);  // in đúng k byte (có thể có 0x00)
                printf("\n");
            }
        } else {
            printf("TIMEOUT\n");
        }
        fflush(stdout);
    }
    close(sender_socket);
    return 0;
}
