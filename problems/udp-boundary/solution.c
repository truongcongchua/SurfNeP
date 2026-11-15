#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_PEERS 1024

typedef struct { struct sockaddr_in addr; unsigned long count; } Peer;
static Peer peers[MAX_PEERS];
static int npeers = 0;

static Peer *lookup(const struct sockaddr_in *a) {
    for (int i = 0; i < npeers; i++)
        if (peers[i].addr.sin_addr.s_addr == a->sin_addr.s_addr && peers[i].addr.sin_port == a->sin_port)
            return &peers[i];
    if (npeers == MAX_PEERS) return NULL;
    peers[npeers].addr = *a;
    peers[npeers].count = 0;
    return &peers[npeers++];
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(s, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind");
        return 1;
    }
    static char buf[65536];
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof from;
        ssize_t n = recvfrom(s, buf, sizeof buf, 0, (struct sockaddr *)&from, &fl);
        if (n < 0) continue;
        Peer *p = lookup(&from);
        char out[64];
        int len = snprintf(out, sizeof out, "LEN %zd %lu", n, p ? ++p->count : 0UL);
        sendto(s, out, (size_t)len, 0, (struct sockaddr *)&from, fl);
    }
}
