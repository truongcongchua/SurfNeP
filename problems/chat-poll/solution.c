#include <arpa/inet.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_FDS 256
#define BUF_SIZE 4096

typedef struct { char id[64]; char buf[BUF_SIZE]; size_t len; } Client;

static struct pollfd fds[MAX_FDS];  // fds[0] là socket lắng nghe
static Client cl[MAX_FDS];          // cl[i] đi kèm fds[i]
static int nfds = 1;

static void send_str(int fd, const char *s) { send(fd, s, strlen(s), MSG_NOSIGNAL); }

static int valid_word(const char *s) { return *s && !strchr(s, ' '); }

static void handle_line(int i, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    if (!cl[i].id[0]) {
        char *sep = strstr(line, ": ");
        if (sep) {
            *sep = 0;
            if (valid_word(line) && valid_word(sep + 2) && strlen(line) < sizeof cl[i].id) {
                strcpy(cl[i].id, line);
                char msg[96];
                snprintf(msg, sizeof msg, "OK %s\n", line);
                send_str(fds[i].fd, msg);
                return;
            }
        }
        send_str(fds[i].fd, "ERROR\n");
        return;
    }
    char msg[BUF_SIZE + 96];
    snprintf(msg, sizeof msg, "%s: %s\n", cl[i].id, line);
    for (int j = 1; j < nfds; j++)
        if (j != i && cl[j].id[0]) send_str(fds[j].fd, msg);
}

static void drop(int i) {
    close(fds[i].fd);
    nfds--;
    fds[i] = fds[nfds];
    cl[i] = cl[nfds];
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    int ls = socket(AF_INET, SOCK_STREAM, 0);
    int yes = 1;
    setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(atoi(argv[1]));
    if (bind(ls, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(ls, 64) < 0) {
        perror("bind/listen");
        return 1;
    }
    fds[0].fd = ls;
    fds[0].events = POLLIN;
    for (;;) {
        if (poll(fds, (nfds_t)nfds, -1) < 0) continue;
        if (fds[0].revents & POLLIN) {
            int c = accept(ls, NULL, NULL);
            if (c >= 0 && nfds < MAX_FDS) {
                fds[nfds].fd = c;
                fds[nfds].events = POLLIN;
                fds[nfds].revents = 0;
                cl[nfds].id[0] = 0;
                cl[nfds].len = 0;
                nfds++;
            } else if (c >= 0) {
                close(c);
            }
        }
        for (int i = 1; i < nfds; i++) {
            if (!(fds[i].revents & (POLLIN | POLLHUP | POLLERR))) continue;
            Client *c = &cl[i];
            ssize_t k = recv(fds[i].fd, c->buf + c->len, BUF_SIZE - 1 - c->len, 0);
            if (k <= 0) {
                drop(i--);  // phần tử cuối được chép vào i: xét lại vị trí i
                continue;
            }
            c->len += (size_t)k;
            c->buf[c->len] = 0;
            char *start = c->buf, *nl;
            while ((nl = strchr(start, '\n'))) {
                *nl = 0;
                handle_line(i, start);
                start = nl + 1;
            }
            c->len -= (size_t)(start - c->buf);
            memmove(c->buf, start, c->len);
            if (c->len == BUF_SIZE - 1) {
                c->buf[c->len] = 0;
                handle_line(i, c->buf);
                c->len = 0;
            }
        }
    }
}
