// SAI có chủ đích: gửi lại strlen(buffer) byte nên cụt ở byte 0x00.
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
    char buffer[1024];
    int bytes_received = recv(client, buffer, sizeof(buffer) - 1, 0);
    if (bytes_received < 0) bytes_received = 0;
    buffer[bytes_received] = '\0';
    send(client, buffer, strlen(buffer), 0);  // SAI: strlen thay vì bytes_received
    close(client);
    close(listener);
    return 0;
}
