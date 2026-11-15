// SAI có chủ đích: đọc thẳng vào struct (padding + thứ tự host), tên cố định.
#include <arpa/inet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

struct rec { uint32_t mssv; uint8_t nlen; char name[16]; uint16_t year; uint8_t m, d; uint16_t gpa; };

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
    for (;;) {
        int c = accept(ls, NULL, NULL);
        struct rec r;
        while (recv(c, &r, sizeof r, 0) > 0) {
            FILE *f = fopen(argv[2], "a");
            fprintf(f, "127.0.0.1 2000-01-01 00:00:00 %u %.*s %u-%02u-%02u %u.%02u\n", r.mssv, r.nlen,
                    r.name, r.year, r.m, r.d, r.gpa / 100, r.gpa % 100);
            fclose(f);
            send(c, "OK\n", 3, MSG_NOSIGNAL);
        }
        close(c);
    }
}
