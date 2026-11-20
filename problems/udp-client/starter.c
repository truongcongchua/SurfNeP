#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <ip> <port>\n", argv[0]);
        return 1;
    }
    // TODO: inet_pton địa chỉ server (sai -> stderr + return 1); socket(AF_INET, SOCK_DGRAM, 0)
    // TODO: với mỗi dòng stdin: bỏ "\r\n" cuối; dòng rỗng -> bỏ qua; sendto cả dòng
    // TODO: poll() chờ socket tối đa 1000 ms; có dữ liệu -> recvfrom, in + "\n", fflush; không -> in "TIMEOUT\n"
    return 0;
}
