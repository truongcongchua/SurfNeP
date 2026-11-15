#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define PHRASE "Ky thuat May tinh"

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    // TODO: socket -> bind -> listen -> accept
    // TODO: recv trong vòng lặp, phát hiện PHRASE kể cả khi nó bị cắt thành nhiều mảnh
    return 0;
}
