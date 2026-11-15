// Lời giải mẫu: giữ lại (len-1) byte cuối của lần nhận trước để bắt chuỗi vắt qua ranh giới.
#define _GNU_SOURCE  // memmem
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
    int listener = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(listener, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(listener, 5) < 0) {
        perror("bind/listen");
        return 1;
    }
    int client = accept(listener, NULL, NULL);
    if (client < 0) {
        perror("accept");
        return 1;
    }

    const size_t plen = strlen(PHRASE);
    char buf[4096 + sizeof PHRASE];
    size_t kept = 0;  // số byte giữ lại từ lần trước ở đầu buf
    for (;;) {
        ssize_t n = recv(client, buf + kept, 4096, 0);
        if (n <= 0)
            break;
        size_t total = kept + (size_t)n;
        if (memmem(buf, total, PHRASE, plen)) {
            send(client, "BYE\n", 4, 0);
            break;
        }
        kept = total < plen - 1 ? total : plen - 1;
        memmove(buf, buf + total - kept, kept);
    }
    close(client);
    close(listener);
    return 0;
}
