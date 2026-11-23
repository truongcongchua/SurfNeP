// SAI có chủ đích: phục vụ một client rồi thoát (thiếu vòng lặp accept).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

int main(int argc, char *argv[]) {
    (void)argc;
    int listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(argv[1]));
    addr.sin_addr.s_addr = INADDR_ANY;
    bind(listener, (struct sockaddr *)&addr, sizeof(addr));
    listen(listener, 5);
    int client = accept(listener, NULL, NULL);
    char message[64];
    sprintf(message, "Hello, client %d!\n", 1);
    send(client, message, strlen(message), 0);
    close(client);
    return 0;
}
