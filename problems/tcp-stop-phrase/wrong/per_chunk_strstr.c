// SAI có chủ đích: chỉ tìm trong từng mảnh vừa nhận -> trượt khi chuỗi bị cắt.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int listener = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    bind(listener, (struct sockaddr *)&addr, sizeof addr);
    listen(listener, 5);
    int client = accept(listener, NULL, NULL);
    char buf[1024];
    ssize_t n;
    while ((n = recv(client, buf, sizeof buf - 1, 0)) > 0) {
        buf[n] = 0;
        if (strstr(buf, "Ky thuat May tinh")) {
            send(client, "BYE\n", 4, 0);
            break;
        }
    }
    close(client);
    return 0;
}
