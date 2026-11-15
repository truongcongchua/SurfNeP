#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#define BUF_SIZE 4096
#define MAX_CLIENTS 64

typedef struct { int fd; int logged; char buf[BUF_SIZE]; size_t len; } Client;
static Client cl[MAX_CLIENTS];

static int send_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t k = send(fd, buf, n, MSG_NOSIGNAL);
        if (k <= 0) return -1;
        buf += k;
        n -= (size_t)k;
    }
    return 0;
}

static void send_str(int fd, const char *s) { send_all(fd, s, strlen(s)); }

// "user pass" (đúng một dấu cách) có trong accounts.txt?
static int check_login(const char *line) {
    const char *sp = strchr(line, ' ');
    if (!sp || sp == line || !sp[1] || strchr(sp + 1, ' ')) return 0;
    FILE *f = fopen("accounts.txt", "r");
    if (!f) return 0;
    char row[256];
    int ok = 0;
    while (!ok && fgets(row, sizeof row, f)) {
        row[strcspn(row, "\r\n")] = 0;
        ok = strcmp(row, line) == 0;
    }
    fclose(f);
    return ok;
}

static void run_command(int c, const char *cmd) {
    char out[64], shell[BUF_SIZE + 128];
    snprintf(out, sizeof out, "out_%d.txt", c);  // mỗi client một tệp riêng
    snprintf(shell, sizeof shell, "%s > %s 2>&1", cmd, out);
    system(shell);  // chặn cả server trong lúc lệnh chạy: hạn chế của select + system
    FILE *f = fopen(out, "rb");
    char *data = NULL;
    size_t len = 0;
    if (f) {
        fseek(f, 0, SEEK_END);
        len = (size_t)ftell(f);
        rewind(f);
        data = malloc(len + 1);
        len = fread(data, 1, len, f);
        fclose(f);
    }
    remove(out);
    char head[64];
    snprintf(head, sizeof head, "OUTPUT %zu\n", len);
    send_str(c, head);
    if (len) send_all(c, data, len);
    free(data);
}

// Xử lý một dòng. Trả về 0 nếu phải đóng client.
static int handle_line(Client *x, char *line) {
    size_t n = strlen(line);
    if (n && line[n - 1] == '\r') line[--n] = 0;
    if (!x->logged) {
        x->logged = check_login(line);
        send_str(x->fd, x->logged ? "LOGIN OK\n" : "LOGIN FAIL\n");
    } else if (!strcmp(line, "exit")) {
        send_str(x->fd, "BYE\n");
        return 0;
    } else {
        run_command(x->fd, line);
    }
    return 1;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <port>\n", argv[0]);
        return 1;
    }
    for (int i = 0; i < MAX_CLIENTS; i++) cl[i].fd = -1;
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
    for (;;) {
        fd_set rd;
        FD_ZERO(&rd);
        FD_SET(ls, &rd);
        int maxfd = ls;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (cl[i].fd >= 0) {
                FD_SET(cl[i].fd, &rd);
                if (cl[i].fd > maxfd) maxfd = cl[i].fd;
            }
        if (select(maxfd + 1, &rd, NULL, NULL, NULL) < 0) continue;
        if (FD_ISSET(ls, &rd)) {
            int c = accept(ls, NULL, NULL);
            int slot = -1;
            for (int i = 0; i < MAX_CLIENTS && slot < 0; i++)
                if (cl[i].fd < 0) slot = i;
            if (c >= 0 && slot < 0) close(c);
            else if (c >= 0) {
                cl[slot].fd = c;
                cl[slot].logged = 0;
                cl[slot].len = 0;
            }
        }
        for (int i = 0; i < MAX_CLIENTS; i++) {
            Client *x = &cl[i];
            if (x->fd < 0 || !FD_ISSET(x->fd, &rd)) continue;
            ssize_t k = recv(x->fd, x->buf + x->len, BUF_SIZE - 1 - x->len, 0);
            int alive = k > 0;
            if (alive) {
                x->len += (size_t)k;
                x->buf[x->len] = 0;
                char *start = x->buf, *nl;
                while (alive && (nl = strchr(start, '\n'))) {
                    *nl = 0;
                    alive = handle_line(x, start);
                    start = nl + 1;
                }
                x->len -= (size_t)(start - x->buf);
                memmove(x->buf, start, x->len);
                if (x->len == BUF_SIZE - 1) x->len = 0;
            }
            if (!alive) {
                close(x->fd);
                x->fd = -1;
            }
        }
    }
}
