// SAI có chủ đích: nộp bản select() cho bài yêu cầu poll() -> CV.
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define MAX_CLIENTS 64
#define BUF_SIZE 4096

typedef struct {
    int fd;              // -1 nếu ô trống
    char id[64];         // rỗng nếu chưa đăng ký
    char buf[BUF_SIZE];  // phần dòng chưa hoàn chỉnh
    size_t len;
} Client;

static Client clients[MAX_CLIENTS];

static void send_str(int fd, const char *s) { send(fd, s, strlen(s), MSG_NOSIGNAL); }

static int valid_word(const char *s) { return *s && !strchr(s, ' '); }

static void handle_line(Client *c, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r')
        line[--n] = 0;
    if (!c->id[0]) {
        char *sep = strstr(line, ": ");
        if (sep) {
            *sep = 0;
            char *name = sep + 2;
            if (valid_word(line) && valid_word(name) && strlen(line) < sizeof c->id) {
                strcpy(c->id, line);
                char msg[128];
                snprintf(msg, sizeof msg, "OK %s\n", c->id);
                send_str(c->fd, msg);
                return;
            }
        }
        send_str(c->fd, "ERROR\n");
        return;
    }
    char msg[BUF_SIZE + 128];
    snprintf(msg, sizeof msg, "%s: %s\n", c->id, line);
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (clients[i].fd >= 0 && &clients[i] != c && clients[i].id[0])
            send_str(clients[i].fd, msg);
}

static void drop(Client *c) {
    close(c->fd);
    c->fd = -1;
    c->id[0] = 0;
    c->len = 0;
}

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
    if (bind(listener, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(listener, 16) < 0) {
        perror("bind/listen");
        return 1;
    }
    for (int i = 0; i < MAX_CLIENTS; i++)
        clients[i].fd = -1;

    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(listener, &rd);
        int maxfd = listener;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (clients[i].fd >= 0) {
                FD_SET(clients[i].fd, &rd);
                if (clients[i].fd > maxfd)
                    maxfd = clients[i].fd;
            }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) {
            perror("select");
            return 1;
        }
        if (FD_ISSET(listener, &rd)) {
            int fd = accept(listener, NULL, NULL);
            int slot = -1;
            for (int i = 0; i < MAX_CLIENTS && slot < 0; i++)
                if (clients[i].fd < 0)
                    slot = i;
            if (fd >= 0 && slot < 0)
                close(fd);
            else if (fd >= 0) {
                clients[slot].fd = fd;
                clients[slot].len = 0;
                clients[slot].id[0] = 0;
            }
        }
        for (int i = 0; i < MAX_CLIENTS; i++) {
            Client *c = &clients[i];
            if (c->fd < 0 || !FD_ISSET(c->fd, &rd))
                continue;
            ssize_t n = recv(c->fd, c->buf + c->len, BUF_SIZE - 1 - c->len, 0);
            if (n <= 0) {
                drop(c);
                continue;
            }
            c->len += (size_t)n;
            c->buf[c->len] = 0;
            char *start = c->buf, *nl;
            while ((nl = strchr(start, '\n'))) {
                *nl = 0;
                handle_line(c, start);
                start = nl + 1;
            }
            c->len -= (size_t)(start - c->buf);
            memmove(c->buf, start, c->len);
            if (c->len == BUF_SIZE - 1) {  // dòng quá dài: xử lý luôn phần đã có
                c->buf[c->len] = 0;
                handle_line(c, c->buf);
                c->len = 0;
            }
        }
    }
}
